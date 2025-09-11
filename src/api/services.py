# src/api/services.py
from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import List, Optional
import re
import csv
import json

from django.conf import settings
from django.db import transaction

from app.parser import FixedWidthParser
from app.transformers import BusinessTransformer
from app.constants import COLUMNS_DB
from .models import Registro

BATCH_SIZE = 1000


def _to_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _normalize_number(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    try:
        Decimal(s)
        return s
    except Exception:
        pass
    s2 = s.replace(".", "").replace(",", ".")
    try:
        Decimal(s2)
        return s2
    except Exception:
        pass
    parts = re.findall(r"\d+|[.,]", s)
    comp = "".join(parts).replace(",", ".")
    pieces = comp.split(".")
    if len(pieces) > 2:
        comp = "".join(pieces[:-1]) + "." + pieces[-1]
    return comp


def _to_decimal(s: str) -> Optional[Decimal]:
    s = _normalize_number(s)
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _write_outputs(records: List[dict], base_name: str) -> dict:
    out_dir = Path(settings.EXPORT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"{base_name}.json"
    csv_path = out_dir / f"{base_name}.csv"

    with json_path.open("w", encoding="utf-8") as jf:
        json.dump(records, jf, ensure_ascii=False, indent=2)

    with csv_path.open("w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=COLUMNS_DB)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r.get(k, "") for k in COLUMNS_DB})


    rel = Path(settings.MEDIA_ROOT).resolve()
    json_rel = Path(json_path).resolve().relative_to(rel) if json_path.is_file() else None
    csv_rel  = Path(csv_path).resolve().relative_to(rel)  if csv_path.is_file()  else None

    return {
        "json_path": str(json_path),
        "csv_path": str(csv_path),
        "json_url": f"{settings.MEDIA_URL}{json_rel}".replace("\\", "/") if json_rel else None,
        "csv_url": f"{settings.MEDIA_URL}{csv_rel}".replace("\\", "/")   if csv_rel  else None,
    }


def procesar_archivo_y_guardar(
    path_txt: str,
    yyyymmdd_override: Optional[str] = None,
    original_name: Optional[str] = None
) -> int:
    """
    Procesa el TXT, genera JSON/CSV y guarda en DB.
    Retorna el total de filas insertadas.
    """
    p = Path(path_txt)
    parser = FixedWidthParser(p, yyyymmdd=yyyymmdd_override)
    transformer = BusinessTransformer(parser.yyyymmdd, original_name or p.name)

    records: List[dict] = []
    buffer: List[Registro] = []
    total = 0

    for cols in parser.iter_rows():
        rec = transformer.build_record(cols).to_dict()
        records.append(rec)

        obj = Registro(
            tipo_documento=rec.get("tipo_documento", ""),
            documento=rec.get("documento", ""),
            nombre=rec.get("nombre", ""),
            producto=rec.get("producto", ""),
            poliza=rec.get("poliza", ""),
            periodo=rec.get("periodo", ""),
            valor_asegurado=_to_decimal(rec.get("valor_asegurado", "")),
            valor_prima=_to_decimal(rec.get("valor_prima", "")),
            doc_cobro=rec.get("doc_cobro", ""),
            fecha_ini=_to_date(rec.get("fecha_ini", "")),
            fecha_fin=None,
            dias=(int(rec.get("dias")) if (rec.get("dias") or "").strip().isdigit() else None),
            telefono_1=rec.get("telefono_1", ""),
            telefono_2=rec.get("telefono_2", ""),
            telefono_3=rec.get("telefono_3", ""),
            ciudad=rec.get("ciudad", ""),
            departamento=rec.get("departamento", ""),
            fecha_venta=_to_date(rec.get("fecha_venta", "")),
            fecha_nacimiento=_to_date(rec.get("fecha_nacimiento", "")),
            tipo_trans=rec.get("tipo_trans", ""),
            beneficiarios=rec.get("beneficiarios", ""),
            genero=rec.get("genero", ""),
            sucursal=rec.get("sucursal", ""),
            tipo_cuenta="",
            ultimos_digitos_cuenta=rec.get("ultimos_digitos_cuenta", ""),
            entidad_bancaria=rec.get("entidad_bancaria", ""),
            nombre_banco=rec.get("nombre_banco", ""),
            estado_debito=rec.get("estado_debito", ""),
            causal_rechazo=rec.get("causal_rechazo", ""),
            codigo_canal=rec.get("codigo_canal", ""),
            descripcion_canal=rec.get("descripcion_canal", ""),
            codigo_estrategia=rec.get("codigo_estrategia", ""),
            tipo_estrategia=rec.get("tipo_estrategia", ""),
            correo_electronico=rec.get("correo_electronico", ""),
            fecha_entrega_colmena=_to_date(rec.get("fecha_entrega_colmena", "")),
            mes_a_trabajar=rec.get("mes_a_trabajar", ""),
            nombre_db=rec.get("nombre_db", ""),
            telefono=(rec.get("telefono", "") == "1"),
            whatsapp=(rec.get("whatsapp", "") == "1"),
            texto=(rec.get("texto", "") == "1"),
            email=(rec.get("email", "") == "1"),
            fisica=(rec.get("fisica", "") == "1"),
            mejor_canal=rec.get("mejor_canal", ""),
            contactar_al=rec.get("contactar_al", ""),
        )

        buffer.append(obj)

        if len(buffer) >= BATCH_SIZE:
            with transaction.atomic():
                Registro.objects.bulk_create(buffer, batch_size=BATCH_SIZE)
            total += len(buffer)
            buffer.clear()

    if buffer:
        with transaction.atomic():
            Registro.objects.bulk_create(buffer, batch_size=BATCH_SIZE)
        total += len(buffer)

    base_name = Path(original_name or p.name).stem
    outs = _write_outputs(records, base_name)
    procesar_archivo_y_guardar._last_outputs = outs  # type: ignore[attr-defined]

    return total
