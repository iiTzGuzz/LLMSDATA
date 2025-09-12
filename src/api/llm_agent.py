# src/api/llm_agent.py
from __future__ import annotations
import os
import re
from typing import Optional, Dict, Any

from django.db import connection

# LangChain
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .services import procesar_archivo_y_guardar


# ----------------------------
# Utilidades de seguridad SQL
# ----------------------------
def _strip_sql_comments(sql: str) -> str:
    return re.sub(r"--.*?$|/\*.*?\*/", "", sql, flags=re.S)

def _is_safe_sql(sql: str) -> bool:
    """Permite solo SELECT/CTE (WITH ... SELECT). Bloquea DML/DDL."""
    sql_clean = _strip_sql_comments(sql).strip().lower()
    if not (sql_clean.startswith("select") or sql_clean.startswith("with")):
        return False
    inseguras = ("insert ", "update ", "delete ", "drop ", "alter ", "create ", "truncate ")
    return not any(k in sql_clean for k in inseguras)

def _targets_allowed_relation(sql: str) -> bool:
    """
    Acepta consultas que mencionen api_registro o la vista api_v_contacto.
    (case-insensitive, ignora comentarios)
    """
    up = _strip_sql_comments(sql).upper()
    return ("API_REGISTRO" in up) or ("API_V_CONTACTO" in up)

def _strip_unaccent(sql: str) -> str:
    """
    Elimina llamadas unaccent(...) para fallback cuando la extensión no existe.
    Implementación simple que reemplaza unaccent(expr) -> expr.
    """
    return re.sub(r"\bunaccent\s*\(([^()]+)\)", r"\1", sql, flags=re.I)


# ----------------------------
# Herramientas
# ----------------------------
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
    Ejecuta SELECT/CTE y devuelve filas JSON. Acepta consultar:
      - api_registro
      - api_v_contacto  (vista recomendada)
    Hace fallback si falla por ausencia de unaccent.
    """
    if not _is_safe_sql(sql):
        return {"ok": False, "error": "Solo se permiten consultas SELECT/CTE.", "tool_used": "consultar_sql_json"}
    if not _targets_allowed_relation(sql):
        return {
            "ok": False,
            "error": "La consulta debe apuntar a api_registro o api_v_contacto.",
            "tool_used": "consultar_sql_json",
        }

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
    if not _targets_allowed_relation(sql):
        return {
            "ok": False,
            "error": "La consulta debe apuntar a api_registro o api_v_contacto.",
            "tool_used": "consultar_sql_texto",
        }

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


# ----------------------------
# Prompt del agente (sistémico)
# ----------------------------
_SYS = """
Eres un agente de datos para una aseguradora.

Herramientas:
- procesar_archivo(path): procesa un TXT e inserta registros en DB.
- consultar_sql_json(sql): ejecuta SELECT y devuelve JSON (por defecto).
- consultar_sql_texto(sql): ejecuta SELECT y devuelve texto tabulado simple.

Objetivo:
- Si el usuario habla de 'procesar/cargar', usa procesar_archivo.
- Si pregunta sobre datos, genera SELECT/CTE seguro y usa consultar_sql_json.
- Responde SIEMPRE con JSON válido y útil.
- Incluye: tool_used y, si es consulta: sql, rows (máx 50) y row_count.

TABLAS/VISTAS:
- Usa por defecto la VISTA **api_v_contacto** (si existe), que ya expone:
  • telefono_principal (teléfono válido normalizado)
  • correo_valido
  • mejor_canal_calc (prioridad: whatsapp > telefono > texto > correo > fisica)
- Si no existe api_v_contacto, incorpora **el siguiente CTE** al inicio de tu consulta y selecciona desde el alias final `calc`:

  WITH base AS (
    SELECT
      id, nombre, documento, poliza, producto,
      btrim(NULLIF(telefono_1, '')) AS t1,
      btrim(NULLIF(telefono_2, '')) AS t2,
      btrim(NULLIF(telefono_3, '')) AS t3,
      btrim(NULLIF(correo_electronico, '')) AS correo,
      COALESCE(whatsapp, false) AS w,
      COALESCE(telefono, false) AS tel,
      COALESCE(texto, false)    AS sms,
      COALESCE(email, false)    AS mail,
      COALESCE(fisica, false)   AS phys,
      fecha_nacimiento, created_at
    FROM api_registro
  ),
  norm AS (
    SELECT *,
           NULLIF(regexp_replace(t1, '\\\\D', '', 'g'), '') AS t1d,
           NULLIF(regexp_replace(t2, '\\\\D', '', 'g'), '') AS t2d,
           NULLIF(regexp_replace(t3, '\\\\D', '', 'g'), '') AS t3d
    FROM base
  ),
  pick AS (
    SELECT *,
           CASE
             WHEN length(t1d) BETWEEN 7 AND 13 AND t1d !~ '^[0]+$' THEN t1d
             WHEN length(t2d) BETWEEN 7 AND 13 AND t2d !~ '^[0]+$' THEN t2d
             WHEN length(t3d) BETWEEN 7 AND 13 AND t3d !~ '^[0]+$' THEN t3d
             ELSE NULL
           END AS telefono_principal,
           CASE
             WHEN correo ~* '^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{{2,}}$' THEN correo
             ELSE NULL
           END AS correo_valido
    FROM norm
  ),
  calc AS (
    SELECT *,
           CASE
             WHEN w   AND telefono_principal IS NOT NULL THEN 'whatsapp'
             WHEN     telefono_principal IS NOT NULL THEN 'telefono'
             WHEN sms AND telefono_principal IS NOT NULL THEN 'texto'
             WHEN correo_valido IS NOT NULL THEN 'correo'
             WHEN phys THEN 'fisica'
             ELSE 'sin_informacion'
           END AS mejor_canal_calc
    FROM pick
  )
  -- A partir de aquí SELECT ... FROM calc

Reglas de TEXTO (búsquedas):
- Si el usuario dice “se llama X”, “llamados X”, “contenga X”, etc., interpreta como coincidencia parcial: ILIKE '%X%'.
- Solo usa igualdad exacta (= 'X') si pide “exactamente X”.
- Usa unaccent(col) ILIKE unaccent('%X%') cuando sea posible. Si llegara a fallar, se aceptará ILIKE simple.

Reglas de EDAD:
- Evita (CURRENT_DATE - fecha_nacimiento) >= INTERVAL 'N years'.
- Mayores de 18:  WHERE fecha_nacimiento <= CURRENT_DATE - INTERVAL '18 years'
- Menores de 18:  WHERE fecha_nacimiento  > CURRENT_DATE - INTERVAL '18 years'

LIMIT y ORDEN:
- Listados: ORDER BY id DESC y LIMIT 50 (salvo que pidan otro límite).

Diccionario de columnas base (api_registro):
- nombre, poliza, producto, valor_prima, correo_electronico, created_at,
  telefono_1, telefono_2, telefono_3,
  whatsapp, telefono, texto, email, fisica,
  estado_debito, causal_rechazo, fecha_nacimiento, fecha_venta, documento

En api_v_contacto / calc encontrarás ya:
- telefono_principal, correo_valido, mejor_canal_calc

Pautas de respuesta:
- Devuelve SIEMPRE JSON con: tool_used, sql, rows (máx 50) y row_count.
- Si el usuario habla de "procesar" archivos, usa la herramienta procesar_archivo.

Ejemplos rápidos (asumiendo que existe api_v_contacto):
- WhatsApp:
  SELECT id, nombre, telefono_principal
  FROM api_v_contacto
  WHERE lower(mejor_canal_calc)='whatsapp'
  ORDER BY id DESC LIMIT 50;

- Nombres que contengan ROBERTO:
  SELECT btrim(nombre) AS nombre
  FROM api_v_contacto
  WHERE unaccent(nombre) ILIKE unaccent('%ROBERTO%')
  ORDER BY id DESC LIMIT 50;

- Menores de 18:
  SELECT id, nombre, fecha_nacimiento, mejor_canal_calc, telefono_principal
  FROM api_v_contacto
  WHERE fecha_nacimiento > CURRENT_DATE - INTERVAL '18 years'
  ORDER BY id DESC LIMIT 50;
"""


# ----------------------------
# Construcción del agente (lazy)
# ----------------------------
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
