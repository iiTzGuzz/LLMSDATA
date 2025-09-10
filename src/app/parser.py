# src/app/parser.py
import re
from pathlib import Path
from typing import Iterator, List
from .constants import WIDTHS
from typing import Optional

# Si ya tienes FILENAME_RE definido arriba, puedes borrar esta definición.
FILENAME_RE = re.compile(r"^([A-Z0-9ÁÉÍÓÚÑ_]+)_(\d{8})\.txt$", re.IGNORECASE)
class FixedWidthParser:
    """
    Lee líneas de 1615 chars y las divide en 22 columnas según WIDTHS.
    Puede tomar la fecha desde el nombre PRUEBA_YYYYMMDD.txt o por override.
    """
    def __init__(self, path: Path, yyyymmdd: str | None = None):
        self.path = Path(path)
        if yyyymmdd:
            self.yyyymmdd = yyyymmdd
        else:
            m = re.search(r"(\d{8})", self.path.name)
            if not m:
                raise ValueError("No se encontró fecha en el nombre y no se proporcionó override 'yyyymmdd'.")
            self.yyyymmdd = m.group(1)

    def _split_line(self, line: str) -> List[str]:
        cols, i = [], 0
        for w in WIDTHS:
            cols.append(line[i:i+w])
            i += w
        return [c.rstrip() for c in cols]

    def iter_rows(self) -> Iterator[list]:
        with self.path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if not line:
                    continue
                yield self._split_line(line)


def normalize_filename(original_name: str, yyyymmdd: Optional[str] = None, default_prefix: str = "PRUEBA") -> str:
    """
    Normaliza cualquier nombre de archivo al formato NOMBRE_YYYYMMDD.txt
    - NOMBRE: en mayúsculas, limpiando caracteres no alfanuméricos a '_'
    - Fecha: usa la que venga en el nombre (si hay 8 dígitos seguidos) o el parámetro yyyymmdd
    - Extensión: fuerza '.txt'
    Levanta ValueError si no puede determinar la fecha.
    """
    # Quitar path y quedarnos con el nombre
    name = original_name.split("/")[-1].split("\\")[-1]

    # ¿Ya cumple el patrón?
    m = FILENAME_RE.match(name)
    if m:
        base = m.group(1)
        fecha = m.group(2)
        return f"{base.upper()}_{fecha}.txt"

    # Intentar extraer fecha del nombre si hay 8 dígitos seguidos
    m8 = re.search(r"(\d{8})", name)
    fecha_en_nombre = m8.group(1) if m8 else None

    # Resolver fecha final
    fecha = None
    if yyyymmdd and len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        fecha = yyyymmdd
    elif fecha_en_nombre:
        fecha = fecha_en_nombre

    if not fecha:
        raise ValueError("No se puede determinar la fecha (YYYYMMDD). Proporcione 'fecha'.")

    # Sacar 'stem' sin extensión para formar el prefijo
    # (si no hay punto, toma todo el nombre)
    if "." in name:
        stem = name.rsplit(".", 1)[0]
    else:
        stem = name

    # Limpiar prefijo: solo letras/números/guion bajo, espacios a '_'
    pref = re.sub(r"[^A-Za-z0-9ÁÉÍÓÚÑáéíóúñ]+", "_", stem).strip("_")
    pref = pref.upper() if pref else default_prefix.upper()

    return f"{pref}_{fecha}.txt"