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


def _strip_unaccent(sql: str) -> str:
    """
    Elimina llamadas unaccent(...) para fallback cuando la extensión no existe.
    Implementación simple que reemplaza unaccent(expr) -> expr.
    """
    return re.sub(r"\bunaccent\s*\(([^()]+)\)", r"\1", sql, flags=re.I)


@tool("procesar_archivo", return_direct=True)
def procesar_archivo(path: str) -> Dict[str, Any]:
    """Procesa un archivo de ancho fijo e inserta registros en DB."""
    try:
        count = procesar_archivo_y_guardar(path)
        return {"ok": True, "insertados": count, "tool_used": "procesar_archivo"}
    except Exception as e:
        return {"ok": False, "error": str(e), "tool_used": "procesar_archivo"}


def _run_sql_to_json(sql: str) -> Dict[str, Any]:
    with connection.cursor() as cur:
        cur.execute(sql)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchall()
    data = [dict(zip(cols, r)) for r in rows] if cols else []
    return {"ok": True, "sql": sql, "rows": data, "row_count": len(data), "tool_used": "consultar_sql_json"}


def _run_sql_to_text(sql: str) -> Dict[str, Any]:
    with connection.cursor() as cur:
        cur.execute(sql)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchall()
    header = " | ".join(cols) if cols else ""
    lines = [header] if header else []
    for r in rows:
        lines.append(" | ".join("" if v is None else str(v) for v in r))
    text = "\n".join(lines)
    return {"ok": True, "sql": sql, "text": text, "row_count": len(rows), "tool_used": "consultar_sql_texto"}


@tool("consultar_sql_json", return_direct=True)
def consultar_sql_json(sql: str) -> Dict[str, Any]:
    """
    Ejecuta SELECTs contra api_registro y devuelve filas como lista de objetos JSON.
    Rechaza cualquier cosa que no sea SELECT/CTE.
    Hace fallback si falla por ausencia de unaccent.
    """
    if not _is_safe_sql(sql):
        return {"ok": False, "error": "Solo se permiten consultas SELECT/CTE.", "tool_used": "consultar_sql_json"}
    if "API_REGISTRO" not in sql.upper():
        return {"ok": False, "error": "La consulta debe apuntar a la tabla api_registro.", "tool_used": "consultar_sql_json"}

    try:
        return _run_sql_to_json(sql)
    except Exception as e:
        err = str(e)
        # Fallback automático si no existe unaccent
        if "unaccent" in err.lower():
            try:
                sql2 = _strip_unaccent(sql)
                out = _run_sql_to_json(sql2)
                out["notice"] = "fallback_sin_unaccent"
                out["original_sql"] = sql
                return out
            except Exception as e2:
                return {"ok": False, "error": str(e2), "sql": sql2, "tool_used": "consultar_sql_json"}
        return {"ok": False, "error": err, "sql": sql, "tool_used": "consultar_sql_json"}


@tool("consultar_sql_texto", return_direct=True)
def consultar_sql_texto(sql: str) -> Dict[str, Any]:
    """
    Igual que consultar_sql_json pero devuelve texto tabulado simple.
    Hace fallback si falla por ausencia de unaccent.
    """
    if not _is_safe_sql(sql):
        return {"ok": False, "error": "Solo se permiten consultas SELECT/CTE.", "tool_used": "consultar_sql_texto"}
    if "API_REGISTRO" not in sql.upper():
        return {"ok": False, "error": "La consulta debe apuntar a la tabla api_registro.", "tool_used": "consultar_sql_texto"}

    try:
        return _run_sql_to_text(sql)
    except Exception as e:
        err = str(e)
        if "unaccent" in err.lower():
            try:
                sql2 = _strip_unaccent(sql)
                out = _run_sql_to_text(sql2)
                out["notice"] = "fallback_sin_unaccent"
                out["original_sql"] = sql
                return out
            except Exception as e2:
                return {"ok": False, "error": str(e2), "sql": sql2, "tool_used": "consultar_sql_texto"}
        return {"ok": False, "error": err, "sql": sql, "tool_used": "consultar_sql_texto"}


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

TABLA: usa SIEMPRE api_registro (nombre exacto). Solo SELECT/CTE, nunca DML/DDL.

Reglas de texto (búsquedas):
- Si el usuario dice “se llama X”, “llamados X”, “que contenga X”, etc., interpreta como coincidencia parcial: ILIKE '%X%'.
- Solo usa igualdad exacta (= 'X') si pide “exactamente X”.
- Usa unaccent(col) ILIKE unaccent('%X%') cuando sea posible. Si falla, ILIKE simple.

Reglas de EDAD:
- Evita (CURRENT_DATE - fecha_nacimiento) >= INTERVAL 'N years'.
- Mayores de 18:
    WHERE fecha_nacimiento <= CURRENT_DATE - INTERVAL '18 years'
  o: WHERE EXTRACT(YEAR FROM AGE(CURRENT_DATE, fecha_nacimiento)) >= 18
- Menores de 18:
    WHERE fecha_nacimiento  > CURRENT_DATE - INTERVAL '18 years'
  o: WHERE EXTRACT(YEAR FROM AGE(CURRENT_DATE, fecha_nacimiento)) < 18

LIMIT y ORDEN:
- Listados: ORDER BY id DESC y LIMIT 50 (salvo que pidan otro límite).

Diccionario de columnas (usa EXACTAMENTE estos nombres en SQL):
- nombre
- poliza
- producto
- valor_prima           (sinónimos: "prima", "valor de la prima")
- correo_electronico    (sinónimos: "correo", "email")
- created_at            (sinónimos: "fecha_creacion", "fecha de creación")
- telefono_1, telefono_2, telefono_3
  · Teléfono principal: COALESCE(NULLIF(telefono_1,''), NULLIF(telefono_2,''), NULLIF(telefono_3,'')) AS telefono_principal
- whatsapp (boolean), telefono (boolean), texto (boolean), email (boolean), fisica (boolean)
- estado_debito, causal_rechazo
  · “débitos rechazados”: (estado_debito ILIKE 'rechaz%' OR NULLIF(causal_rechazo,'') IS NOT NULL)
  · “últimos N días”: created_at >= CURRENT_DATE - INTERVAL '<N> days'
- fecha_nacimiento, fecha_venta

MEJOR CANAL (cálculo dinámico, NO usar la columna mejor_canal almacenada):
- Prioridad: WhatsApp > Teléfono (llamada) > Mensaje de texto (SMS) > Correo electrónico > Correspondencia física.
- Reglas (requiere dato disponible para ese canal):
  · WhatsApp/Teléfono/SMS: requieren teléfono principal no vacío.
  · Correo: requiere correo_electronico no vacío y con '@'.
  · Física: sin requisito adicional.
- Implementa SIEMPRE este CASE (ajústalo a la consulta):
  CASE
    WHEN whatsapp AND COALESCE(NULLIF(telefono_1,''), NULLIF(telefono_2,''), NULLIF(telefono_3,'')) IS NOT NULL THEN 'whatsapp'
    WHEN telefono AND COALESCE(NULLIF(telefono_1,''), NULLIF(telefono_2,''), NULLIF(telefono_3,'')) IS NOT NULL THEN 'telefono'
    WHEN texto    AND COALESCE(NULLIF(telefono_1,''), NULLIF(telefono_2,''), NULLIF(telefono_3,'')) IS NOT NULL THEN 'texto'
    WHEN email    AND NULLIF(correo_electronico,'') IS NOT NULL AND POSITION('@' IN correo_electronico) > 1 THEN 'correo'
    WHEN fisica   THEN 'fisica'
    ELSE 'sin_informacion'
  END AS mejor_canal_calc

- Si el usuario pide “mejor canal sea WhatsApp”, filtra sobre ese cálculo:
  · Opción A (subconsulta recomendable):
      SELECT *
      FROM (
        SELECT
          ...,
          COALESCE(NULLIF(telefono_1,''), NULLIF(telefono_2,''), NULLIF(telefono_3,'')) AS telefono_principal,
          CASE ... END AS mejor_canal_calc
        FROM api_registro
      ) t
      WHERE LOWER(mejor_canal_calc) = 'whatsapp'
      ORDER BY id DESC
      LIMIT 50;

  · Opción B (repetir CASE en WHERE) está permitido, pero es preferible la subconsulta.

Notas:
- Para “teléfono principal”, expón el alias telefono_principal.
- Para WhatsApp u otros canales en filtros, usa comparación insensible a mayúsculas: LOWER(mejor_canal_calc) = 'whatsapp'.

Reglas de respuesta:
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
