# src/app/transformers.py
from __future__ import annotations
import unicodedata
from typing import List
from .domain import Record
from .constants import (
    PHR_TELEFONO, PHR_WHATS, PHR_TEXTO, PHR_EMAIL, PHR_FISICA,
    CHANNEL_PRIORITY,
)

def _norm(s: str) -> str:
    s = s or ""
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

def _has_any(text: str, phrases) -> bool:
    t = _norm(text)
    return any(_norm(p) in t for p in phrases)

def _first_phone(p1: str, p2: str, p3: str) -> str:
    for p in (p1 or "", p2 or "", p3 or ""):
        p = p.strip()
        if p:
            return p
    return ""

class BusinessTransformer:
    """
    Aplica reglas del enunciado para mapear las 22 columnas del TXT a las
    columnas destino y calcula flags de canales, mejor_canal y contactar_al.
    """
    def __init__(self, yyyymmdd: str, file_name: str):
        self.yyyymmdd = yyyymmdd
        self.file_name = file_name

    def build_record(self, cols: List[str]) -> Record:
        # --- normalización defensiva ---
        # Acepta lista/tupla directamente; si llega un objeto con .cols, lo toma.
        if hasattr(cols, "cols"):
            cols = cols.cols  # type: ignore[attr-defined]
        if not isinstance(cols, (list, tuple)):
            raise TypeError(f"Se esperaba list/tuple de 22 columnas, llegó: {type(cols)}")
        if len(cols) != 22:
            raise ValueError(f"Se esperaban 22 columnas, llegaron: {len(cols)}")
        # --- fin normalización ---

        (
            c1,  # (vacío)
            c2,  # tipo_documento
            c3,  # documento
            c4,  # nombre
            c5,  # producto+poliza
            c6,  # periodo+valor_asegurado
            c7,  # valor_prima
            c8,  # doc_cobro
            c9,  # fecha_ini
            c10, # dias
            c11, # telefono_1
            c12, # telefono_2
            c13, # telefono_3
            c14, # ciudad
            c15, # departamento
            c16, # fecha_venta(10) + fecha_nacimiento(10) + tipo_trans(3) + beneficiarios(resto)
            c17, # genero(1) + sucursal(resto)
            c18, # ultimos_digitos_cuenta
            c19, # entidad_bancaria
            c20, # nombre_banco
            c21, # estado_debito
            c22, # preferencias texto libre
        ) = cols

        # Producto / póliza
        producto = (c5[:5] or "").strip()
        poliza = (c5[5:] or "").strip()

        # Periodo y valor_asegurado
        periodo = (c6[:1] or "").strip()
        valor_asegurado = (c6[1:] or "").strip()

        # Fechas en bloque 16
        fecha_venta      = (c16[0:10]  or "").strip()
        fecha_nacimiento = (c16[10:20] or "").strip()
        tipo_trans       = (c16[20:23] or "").strip()
        beneficiarios    = (c16[23:]   or "").strip()

        # Genero y sucursal (col17)
        genero   = (c17[:1] or "").strip()
        sucursal = (c17[1:] or "").strip()

        # Flags desde "preferencias" (c22)
        preferencias = c22 or ""
        telefono_f = "1" if _has_any(preferencias, PHR_TELEFONO) else ""
        whatsapp_f = "1" if _has_any(preferencias, PHR_WHATS)   else ""
        texto_f    = "1" if _has_any(preferencias, PHR_TEXTO)   else ""
        email_f    = "1" if _has_any(preferencias, PHR_EMAIL)   else ""
        fisica_f   = "1" if _has_any(preferencias, PHR_FISICA)  else ""

        # Mejor canal según prioridad
        activos = {
            "texto": bool(texto_f),
            "email": bool(email_f),
            "telefono": bool(telefono_f),
            "whatsapp": bool(whatsapp_f),
            "fisica": bool(fisica_f),
        }
        mejor = next((c for c in CHANNEL_PRIORITY if activos.get(c)), None) or "texto"

        # contactar_al
        contactar = ""
        if mejor in ("texto", "telefono", "whatsapp"):
            contactar = _first_phone(c11, c12, c13)
            # Si no hay teléfono y hay correo, el fallback lo maneja la fase de consultas.
        elif mejor == "email":
            # En este dataset base el correo puede venir vacío.
            pass

        # fecha_entrega_colmena y mes_a_trabajar desde self.yyyymmdd
        fec = f"{self.yyyymmdd[0:4]}-{self.yyyymmdd[4:6]}-{self.yyyymmdd[6:8]}"
        mes = self.yyyymmdd[4:6]

        return Record(
            tipo_documento=c2.strip(),
            documento=c3.strip(),
            nombre=c4.strip(),
            producto=producto,
            poliza=poliza,
            periodo=periodo,
            valor_asegurado=valor_asegurado,
            valor_prima=c7.strip(),
            doc_cobro=c8.strip(),
            fecha_ini=(c9.strip()[:10] if c9.strip() else ""),
            fecha_fin="",
            dias=c10.strip(),
            telefono_1=c11.strip(),
            telefono_2=c12.strip(),
            telefono_3=c13.strip(),
            ciudad=c14.strip(),
            departamento=c15.strip(),
            fecha_venta=fecha_venta,
            fecha_nacimiento=fecha_nacimiento,
            tipo_trans=tipo_trans,
            beneficiarios=beneficiarios,
            genero=genero,
            sucursal=sucursal,
            tipo_cuenta="",
            ultimos_digitos_cuenta=c18.strip(),
            entidad_bancaria=c19.strip(),
            nombre_banco=c20.strip(),
            estado_debito=c21.strip(),
            causal_rechazo="",
            codigo_canal="",
            descripcion_canal="",
            codigo_estrategia="",
            tipo_estrategia="",
            correo_electronico="",
            fecha_entrega_colmena=fec,
            mes_a_trabajar=mes,
            id="",
            nombre_db=self.file_name,
            telefono=telefono_f,
            whatsapp=whatsapp_f,
            texto=texto_f,
            email=email_f,
            fisica=fisica_f,
            mejor_canal=mejor,
            contactar_al=contactar,
        )
