from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
from typing import Dict, Any, Optional, List

@dataclass(slots=True)
class RawRow:
    """Fila cruda extraída del TXT por intervalos."""
    cols: List[str]           # columnas crudas (col1..colN)
    line_no: int              # número de línea (para trazabilidad)

@dataclass(slots=True)
class Record:
    # Campos finales (exactamente COLUMNS_DB)
    tipo_documento: str = ""
    documento: str = ""
    nombre: str = ""
    producto: str = ""
    poliza: str = ""
    periodo: str = ""
    valor_asegurado: str = ""
    valor_prima: str = ""
    doc_cobro: str = ""
    fecha_ini: str = ""
    fecha_fin: str = ""         # vacío por regla
    dias: str = ""
    telefono_1: str = ""
    telefono_2: str = ""
    telefono_3: str = ""
    ciudad: str = ""
    departamento: str = ""
    fecha_venta: str = ""       # YYYY-MM-DD si viene bien formado
    fecha_nacimiento: str = ""  # YYYY-MM-DD
    tipo_trans: str = ""
    beneficiarios: str = ""
    genero: str = ""
    sucursal: str = ""
    tipo_cuenta: str = ""       # vacío por regla
    ultimos_digitos_cuenta: str = ""
    entidad_bancaria: str = ""
    nombre_banco: str = ""
    estado_debito: str = ""
    causal_rechazo: str = ""
    codigo_canal: str = ""
    descripcion_canal: str = ""
    codigo_estrategia: str = ""
    tipo_estrategia: str = ""
    correo_electronico: str = ""
    fecha_entrega_colmena: str = ""  # YYYY-MM-DD
    mes_a_trabajar: str = ""         # MM (numérico)
    id: str = ""                     # vacío por regla
    nombre_db: str = ""
    telefono: str = ""               # flags derivados (1 / "")
    whatsapp: str = ""
    texto: str = ""
    email: str = ""
    fisica: str = ""
    mejor_canal: str = ""            # calculados
    contactar_al: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class InvalidFilenameError(Exception): ...
class BadLineLengthWarning(UserWarning): ...
