# src/api/llm_agent.py
from __future__ import annotations
import os
import re
from typing import Optional, Dict, Any

from django.db import connection

# LangChain (usar las rutas modernas estables)
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .services import procesar_archivo_y_guardar


def _is_safe_sql(sql: str) -> bool:
    """Permite solo SELECT/CTE (WITH ... SELECT). Bloquea DML/DDL."""
    # Quita comentarios y normaliza
    sql_clean = re.sub(r"--.*?$|/\*.*?\*/", "", sql, flags=re.S).strip().lower()
    if not (sql_clean.startswith("select") or sql_clean.startswith("with")):
        return False
    # Palabras peligrosas de DDL/DML
    inseguras = ("insert ", "update ", "delete ", "drop ", "alter ", "create ", "truncate ")
    return not any(k in sql_clean for k in inseguras)


@tool("procesar_archivo", return_direct=True)
def procesar_archivo(path: str) -> Dict[str, Any]:
    """Procesa un archivo de ancho fijo e inserta registros en DB."""
    try:
        count = procesar_archivo_y_guardar(path)
        return {"ok": True, "insertados": count}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool("consultar_sql_json", return_direct=True)
def consultar_sql_json(sql: str) -> Dict[str, Any]:
    """
    Ejecuta SELECTs contra api_registro y devuelve filas como lista de objetos JSON.
    Rechaza cualquier cosa que no sea SELECT/CTE.
    """
    if not _is_safe_sql(sql):
        return {"ok": False, "error": "Solo se permiten consultas SELECT/CTE."}
    # Seguridad adicional: la consulta debe apuntar a la tabla principal
    if "API_REGISTRO" not in sql.upper():
        return {"ok": False, "error": "La consulta debe apuntar a la tabla api_registro."}

    try:
        with connection.cursor() as cur:
            cur.execute(sql)
            cols = [c[0] for c in cur.description] if cur.description else []
            rows = cur.fetchall()
        data = [dict(zip(cols, r)) for r in rows] if cols else []
        return {"ok": True, "sql": sql, "rows": data, "row_count": len(data)}
    except Exception as e:
        return {"ok": False, "error": str(e), "sql": sql}


@tool("consultar_sql_texto", return_direct=True)
def consultar_sql_texto(sql: str) -> Dict[str, Any]:
    """
    Igual que consultar_sql_json pero devuelve texto tabulado simple.
    Úsalo solo si el usuario pide texto crudo/tablas.
    """
    if not _is_safe_sql(sql):
        return {"ok": False, "error": "Solo se permiten consultas SELECT/CTE."}
    if "API_REGISTRO" not in sql.upper():
        return {"ok": False, "error": "La consulta debe apuntar a la tabla api_registro."}

    try:
        with connection.cursor() as cur:
            cur.execute(sql)
            cols = [c[0] for c in cur.description] if cur.description else []
            rows = cur.fetchall()
        header = " | ".join(cols) if cols else ""
        lines = [header] if header else []
        for r in rows:
            lines.append(" | ".join("" if v is None else str(v) for v in r))
        text = "\n".join(lines)
        return {"ok": True, "sql": sql, "text": text, "row_count": len(rows)}
    except Exception as e:
        return {"ok": False, "error": str(e), "sql": sql}


tools = [procesar_archivo, consultar_sql_json, consultar_sql_texto]

_SYS = """Eres un agente de datos para una aseguradora.

Herramientas:
- procesar_archivo(path): procesa un TXT e inserta registros en DB.
- consultar_sql_json(sql): ejecuta SELECT y devuelve JSON (usa esta por defecto).
- consultar_sql_texto(sql): ejecuta SELECT y devuelve texto tabulado simple.

Objetivo:
- Si el usuario habla de 'procesar/cargar', usa procesar_archivo.
- Si pregunta sobre datos, genera SELECT seguro y usa consultar_sql_json.
- Responde SIEMPRE con JSON válido y útil.
- Incluye: tool_used y, si es consulta: sql, rows (máx 50) y row_count.

Tabla: api_registro (ver columnas en el modelo).
Notas:
- 'menores de 18 años': edad con CURRENT_DATE - fecha_nacimiento.
- Limita a 50 con ORDER BY id DESC cuando aplique.

Reglas de edad:
- Mayores de 18: WHERE fecha_nacimiento <= CURRENT_DATE - INTERVAL '18 years'
- Menores de 18: WHERE fecha_nacimiento >  CURRENT_DATE - INTERVAL '18 years'
- Evita expresiones como (CURRENT_DATE - fecha_nacimiento) >= INTERVAL '18 years'

TABLA: usa SIEMPRE api_registro.

Diccionario de columnas (usa EXACTAMENTE estos nombres en SQL):
- nombre
- poliza
- producto
- valor_prima           (sinónimos del usuario: "prima", "valor de la prima")
- correo_electronico    (sinónimos: "correo", "email")
- created_at            (sinónimos: "fecha_creacion", "fecha de creación")
- telefono_1, telefono_2, telefono_3
  • Si piden "teléfono principal": usa COALESCE(NULLIF(telefono_1,''), NULLIF(telefono_2,''), NULLIF(telefono_3,'')) AS telefono_principal
- mejor_canal           (sinónimos: "canal preferido"; para WhatsApp usa LOWER(mejor_canal) = 'whatsapp')
- estado_debito, causal_rechazo
  • Si piden “débitos rechazados”: filtra con (estado_debito ILIKE 'rechaz%' OR NULLIF(causal_rechazo,'') IS NOT NULL)
  • Para “últimos N días” usa created_at >= CURRENT_DATE - INTERVAL '<N> days'
- fecha_nacimiento      (edad: EXTRACT(YEAR FROM AGE(CURRENT_DATE, fecha_nacimiento)))
- fecha_venta

Reglas de consulta:
- Solo SELECT/CTE.
- Si piden listados, ORDER BY id DESC y LIMIT 50 (o el límite que pidan).
- Devuelve SIEMPRE JSON con: tool_used, sql, rows (máx 50) y row_count.
- Si el usuario habla de "procesar" archivos, usa la herramienta procesar_archivo.
"""


_agent: Optional[AgentExecutor] = None


def get_agent() -> AgentExecutor:
    """
    Crea el agente (lazy) una sola vez.
    No se ejecuta al importar el módulo para evitar fallos en arranque.
    """
    global _agent
    if _agent is not None:
        return _agent

    # Import lazy para no reventar si falta el paquete en build
    try:
        from langchain_openai import ChatOpenAI
    except Exception as e:
        raise RuntimeError(
            "Falta 'langchain-openai'. Asegúrate de tenerlo en requirements.txt y rebuild."
        ) from e

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY no configurada en el entorno.")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYS),
        ("human", "{instruccion}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    _agent = AgentExecutor(agent=agent, tools=tools, verbose=False, handle_parsing_errors=True)
    return _agent
