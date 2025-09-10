from __future__ import annotations
import csv, json
from pathlib import Path
from typing import Iterable, List, Dict
from .constants import COLUMNS_DB
from .domain import Record

class OutputWriter:
    @staticmethod
    def to_csv(records: Iterable[Record], path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS_DB)
            w.writeheader()
            for r in records:
                w.writerow(r.to_dict())

    @staticmethod
    def to_json(records: Iterable[Record], path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = [r.to_dict() for r in records]
        with p.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
