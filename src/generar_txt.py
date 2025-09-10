import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

fake = Faker("es_CO")

# ----- Configuración -----
OUTPUT_PATH = Path("PRUEBAS_20250529.txt")  # nombre y fecha del archivo
NUM_REGISTROS = 80

# Intervalos exactos (longitudes) según el enunciado
# (0-10),(10-13),(13-28),(28-128),(128-143),(143-165),(165-187),
# (187-201),(201-221),(221-226),(226-241),(241-256),(256-271),
# (271-321),(321-371),(371-494),(494-548),(548-568),(568-575),
# (575-615),(615-625),(625-1615)
WIDTHS = [
    10, 3, 15, 100, 15, 22, 22,
    14, 20, 5, 15, 15, 15,
    50, 50, 123, 54, 20, 7,
    40, 10, 990
]

# Preferencias posibles (tal cual frases del enunciado)
PREFERENCIAS = [
    "Línea telefónica",
    "Mensaje de texto",
    "Correo electrónico",
    "whastapp",  # (sic) así viene en el enunciado
    "Correspondencia fisica",
    "Línea telefónica, Mensaje de texto, Correo electrónico",
    "Mensaje de texto, whastapp",
    "Correo electrónico, Correspondencia fisica",
    "Línea telefónica, whastapp",
    "Mensaje de texto",
    "Correo electrónico",
    "Correspondencia fisica"
]

# Departamentos de Colombia
DEPARTAMENTOS = [
    "Antioquia","Atlántico","Bogotá D.C.","Bolívar","Boyacá","Caldas","Caquetá","Casanare","Cauca",
    "Cesar","Chocó","Córdoba","Cundinamarca","Guainía","Guaviare","Huila","La Guajira","Magdalena",
    "Meta","Nariño","Norte de Santander","Putumayo","Quindío","Risaralda","San Andrés y Providencia",
    "Santander","Sucre","Tolima","Valle del Cauca","Vaupés","Vichada","Arauca","Amazonas"
]

def fit(value: str, width: int) -> str:
    """
    Ajusta el valor a 'width' caracteres: trunca si es más largo o
    rellena con espacios a la derecha si es más corto.
    """
    v = (value or "")
    if len(v) > width:
        return v[:width]
    return v.ljust(width)

def rand_date(start: str, end: str) -> str:
    sd = datetime.strptime(start, "%Y-%m-%d")
    ed = datetime.strptime(end, "%Y-%m-%d")
    delta = (ed - sd).days
    return (sd + timedelta(days=random.randint(0, delta))).strftime("%Y-%m-%d")

def generar_linea() -> str:
    # Col1 (desconocida en reglas) -> dejamos vacío (10 espacios)
    col1 = ""

    # Col2: tipo_documento (pero en reglas dice que tipo_documento es "columna 2", aquí col2 es DOC TIPO)
    # OJO: según enunciado, tipo_documento sale de "columna 2", documento de "columna 3", nombre de "columna 4".
    # Por lo tanto, col2, col3, col4 deben mapear a esos 3 respectivamente.
    tipo_documento = random.choice(["CC","CE","TI"])

    # Col3: documento (numérico corto en ancho 15 segun intervalos? No, ojo: ancho de col3 es 15.)
    # El intervalo 13-28 => 15. Usaremos un ID de 8-10 dígitos y lo ajustamos.
    documento = str(random.randint(10_000_000, 99_999_999))

    # Col4: nombre (intervalo 28-128 => 100)
    nombre = fake.name()

    # Col5: producto+poliza (intervalo 128-143 => 15)
    # Reglas: producto = 5 primeros, póliza = el resto
    # Aquí guardamos ambos juntos, p.ej. "VIDA1POL000123"
    prod = random.choice(["VIDA","AUTO","HOGAR","SALU","DENT"])
    producto_poliza = (prod + str(random.randint(0,9)) + f"POL{random.randint(1000,9999)}")

    # Col6: periodo + valor_asegurado (intervalo 143-165 => 22)
    # periodo = primer caracter; valor_asegurado = el resto
    periodo = str(random.randint(1,9))
    valor_asegurado = str(random.randint(5_000_000, 50_000_000))

    # Col7: valor_prima (intervalo 165-187 => 22)
    valor_prima = str(random.randint(80_000, 900_000))

    # Col8: doc_cobro (187-201 => 14)
    doc_cobro = f"DOC{random.randint(1000,9999)}"

    # Col9: fecha_ini (201-221 => 20)
    fecha_ini = rand_date("2023-01-01","2025-08-31")

    # Col10: dias (221-226 => 5)
    dias = str(random.randint(30, 365))

    # Col11-13: teléfonos (15 cada una)
    telefono_1 = str(random.randint(3000000000, 3999999999))
    telefono_2 = str(random.randint(3000000000, 3999999999))
    telefono_3 = str(random.randint(3000000000, 3999999999))

    # Col14: ciudad (50)
    ciudad = fake.city()

    # Col15: departamento (50) — usamos lista fija
    departamento = random.choice(DEPARTAMENTOS)

    # Col16: bloque (123) => 10 chars f_venta + 10 f_nac + 3 tipo_trans + resto beneficiarios
    fecha_venta = rand_date("2023-01-01","2025-08-31")       # 10
    fecha_nac = rand_date("1970-01-01","2007-12-31")         # 10
    tipo_trans = random.choice(["001","002","003"])          # 3
    beneficiarios = fake.name()                               # resto
    bloque_16 = f"{fecha_venta}{fecha_nac}{tipo_trans}{beneficiarios}"

    # Col17: genero + sucursal (54) => 1 char + resto
    genero = random.choice(["M","F"])
    sucursal = fake.company()

    # Col18: ultimos_digitos_cuenta (20)
    ultimos_digitos_cuenta = str(random.randint(1000,9999))

    # Col19: entidad_bancaria (7)
    entidad_bancaria = random.choice(["BBVA","Bcol","Davv","BCS","BPOP","AVVl","FNA"])

    # Col20: nombre_banco (40)
    nombre_banco = random.choice(["Banco Principal","Banco Central","Banco del Norte"])

    # Col21: estado_debito (10)
    estado_debito = random.choice(["OK","ERR","PEND"])

    # Col22: preferencias (990) — frases del enunciado
    preferencias = random.choice(PREFERENCIAS)

    # ---- Ajuste a cada ancho ----
    values = [
        col1,
        tipo_documento,
        documento,
        nombre,
        producto_poliza,
        periodo + valor_asegurado,   # col6 empaqueta ambos
        valor_prima,
        doc_cobro,
        fecha_ini,
        dias,
        telefono_1,
        telefono_2,
        telefono_3,
        ciudad,
        departamento,
        bloque_16,
        genero + " " + sucursal,
        ultimos_digitos_cuenta,
        entidad_bancaria,
        nombre_banco,
        estado_debito,
        preferencias,
    ]

    fixed = [fit(v, w) for v, w in zip(values, WIDTHS)]
    line = "".join(fixed)
    # Seguridad: cada línea debe tener exactamente 1615 chars
    if len(line) != 1615:
        # Si por alguna razón se desfasó (acentos no deberían afectar, pero por si acaso),
        # recortamos o rellenamos al tamaño final.
        if len(line) > 1615:
            line = line[:1615]
        else:
            line = line.ljust(1615)
    return line + "\n"

def generar_archivo(num=NUM_REGISTROS):
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for _ in range(num):
            f.write(generar_linea())
    print(f"✅ Archivo generado: {OUTPUT_PATH.resolve()}")
    print(f"📄 Registros: {num}")

if __name__ == "__main__":
    generar_archivo()
