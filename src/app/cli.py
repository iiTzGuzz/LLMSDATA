from __future__ import annotations
import argparse
from pathlib import Path
from typing import List
from .parser import FixedWidthParser
from .transformers import BusinessTransformer
from .writer import OutputWriter

def run_cli() -> None:
    ap = argparse.ArgumentParser(
        description="ETL Fase 1: TXT ancho fijo -> JSON/CSV"
    )
    ap.add_argument("input", help="Ruta del archivo PRUEBA_YYYYMMDD.txt")
    ap.add_argument("--out-csv", default="out/salida.csv", help="Ruta CSV de salida")
    ap.add_argument("--out-json", default="out/salida.json", help="Ruta JSON de salida")
    args = ap.parse_args()

    parser = FixedWidthParser(args.input)
    transformer = BusinessTransformer(
        filename_stem_date=parser.yyyymmdd,
        filename_full=Path(args.input).name
    )

    records = [transformer.build_record(row) for row in parser.iter_rows()]
    OutputWriter.to_csv(records, args.out_csv)
    OutputWriter.to_json(records, args.out_json)

    print(f"✅ Registros procesados: {len(records)}")
    print(f"📄 CSV:  {Path(args.out_csv).resolve()}")
    print(f"🧩 JSON: {Path(args.out_json).resolve()}")
