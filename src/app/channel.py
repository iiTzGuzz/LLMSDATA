from __future__ import annotations
from typing import Tuple
from .constants import CHANNEL_PRIORITY

def pick_phone(telefono_1: str, telefono_2: str, telefono_3: str) -> str:
    for t in (telefono_1, telefono_2, telefono_3):
        if t:
            return t
    return ""

def resolve_best_channel(
    flags: dict,  # {"texto": "1"/"", "email": "1"/"", "telefono": "1"/"", "whatsapp": "1"/"", "fisica": "1"/""}
    telefono_1: str, telefono_2: str, telefono_3: str,
    correo_electronico: str
) -> Tuple[str, str]:
    """
    Devuelve (mejor_canal, contactar_al) aplicando las reglas:
    - prioriza: texto > email > teléfono > whatsapp > físico
    - si no hay ningún canal en 1, se asume texto (por defecto)
    - para texto/teléfono/whatsapp se requiere teléfono. Si no hay, probar correo.
    - si mejor es email, requiere correo; si no, probar canales telefónicos con número.
    - si nada sirve, ambos vacíos.
    """
    # Normalizamos a booleanos
    active = {k: (v == "1") for k, v in flags.items()}

    if not any(active.values()):
        # Por defecto: texto
        candidate = "texto"
    else:
        candidate = next((c for c in CHANNEL_PRIORITY if active.get(c)), "texto")

    def phone_or_email(chan: str) -> Tuple[str, str]:
        phone = pick_phone(telefono_1, telefono_2, telefono_3)
        if chan in ("texto", "telefono", "whatsapp"):
            if phone:
                return chan, phone
            # fallback a email si existe
            if correo_electronico:
                return "email", correo_electronico
            return chan, ""  # sin contacto posible
        # canal email
        if chan == "email":
            if correo_electronico:
                return "email", correo_electronico
            # fallback a canales telefónicos si hay y con número
            if any(active.get(c) for c in ("texto","telefono","whatsapp")) and pick_phone(telefono_1, telefono_2, telefono_3):
                return "texto" if active.get("texto") else ("telefono" if active.get("telefono") else "whatsapp"), pick_phone(telefono_1, telefono_2, telefono_3)
            return "email", ""
        # físico no requiere dato de contacto
        return "fisica", ""

    return phone_or_email(candidate)
