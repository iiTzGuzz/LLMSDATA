# src/app/constants.py
from __future__ import annotations
from typing import Final, List, Tuple
import re

# ------------------------------
# Nombre de archivo esperado: <NOMBRE>_<YYYYMMDD>.txt (case-insensitive)
# Ej.: CLIENTES_20250529.txt, Prueba_20250529.txt
# Group 1 = NOMBRE, Group 2 = YYYYMMDD
# ------------------------------
FILENAME_RE: Final[re.Pattern[str]] = re.compile(r"^([A-Za-z0-9._-]+)_(\d{8})\.txt$", re.IGNORECASE)

# ------------------------------
# Intervalos de ancho fijo [inicio, fin) (0-index, fin excluido)
# (22 intervalos del enunciado)
# ------------------------------
INTERVALS: Final[List[Tuple[int, int]]] = [
    (0,10),(10,13),(13,28),(28,128),(128,143),(143,165),(165,187),
    (187,201),(201,221),(221,226),(226,241),(241,256),(256,271),
    (271,321),(321,371),(371,494),(494,548),(548,568),(568,575),
    (575,615),(615,625),(625,1615)
]

# Anchos calculados a partir de INTERVALS (útiles para el parser)
WIDTHS: Final[List[int]] = [b - a for a, b in INTERVALS]

# Sanity checks
assert len(INTERVALS) == 22, "Deben ser 22 intervalos."
assert sum(WIDTHS) == 1615, "La suma de anchos debe ser 1615."

# ------------------------------
# Columnas destino (CSV/DB)
# ------------------------------
COLUMNS_DB: Final[List[str]] = [
    'tipo_documento','documento','nombre','producto','poliza','periodo','valor_asegurado',
    'valor_prima','doc_cobro','fecha_ini','fecha_fin','dias','telefono_1','telefono_2','telefono_3',
    'ciudad','departamento','fecha_venta','fecha_nacimiento','tipo_trans','beneficiarios','genero',
    'sucursal','tipo_cuenta','ultimos_digitos_cuenta','entidad_bancaria','nombre_banco',
    'estado_debito','causal_rechazo','codigo_canal','descripcion_canal','codigo_estrategia',
    'tipo_estrategia','correo_electronico','fecha_entrega_colmena','mes_a_trabajar','id',
    'nombre_db','telefono','whatsapp','texto','email','fisica','mejor_canal','contactar_al'
]

# ------------------------------
# Frases en la columna de preferencias (como vienen en el enunciado)
# ------------------------------
PHRASE_TELEFONO: Final[str] = "Línea telefónica"
PHRASE_WHATSAPP: Final[str] = "whastapp"  # (sic)
PHRASE_TEXTO: Final[str] = "Mensaje de texto"
PHRASE_EMAIL: Final[str] = "Correo electrónico"
PHRASE_FISICA: Final[str] = "Correspondencia fisica"

# Variantes normalizadas para búsquedas (sin/ con tilde)
# Útiles si tu lógica hace matching case-insensitive y sin acentos
PHR_TELEFONO: Final[tuple[str, ...]] = ("linea telefonica", "línea telefónica")
PHR_WHATS:    Final[tuple[str, ...]] = ("whastapp", "whatsapp")
PHR_TEXTO:    Final[tuple[str, ...]] = ("mensaje de texto",)
PHR_EMAIL:    Final[tuple[str, ...]] = ("correo electronico", "correo electrónico")
PHR_FISICA:   Final[tuple[str, ...]] = ("correspondencia fisica", "correspondencia física")

# ------------------------------
# Prioridad de canales
# ------------------------------
CHANNEL_PRIORITY: Final[List[str]] = ["texto", "email", "telefono", "whatsapp", "fisica"]

__all__ = [
    "FILENAME_RE",
    "INTERVALS", "WIDTHS",
    "COLUMNS_DB",
    "PHRASE_TELEFONO", "PHRASE_WHATSAPP", "PHRASE_TEXTO", "PHRASE_EMAIL", "PHRASE_FISICA",
    "PHR_TELEFONO", "PHR_WHATS", "PHR_TEXTO", "PHR_EMAIL", "PHR_FISICA",
    "CHANNEL_PRIORITY",
]
