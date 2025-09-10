import os
from psycopg import connect
from dotenv import load_dotenv

# Carga .env desde src
load_dotenv()

print("ENV:",
      repr(os.getenv("POSTGRES_DB")),
      repr(os.getenv("POSTGRES_USER")),
      repr(os.getenv("POSTGRES_PASSWORD")),
      repr(os.getenv("POSTGRES_HOST")),
      repr(os.getenv("POSTGRES_PORT")))

with connect(
    dbname=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=os.getenv("POSTGRES_PORT"),
    options="-c client_encoding=UTF8",
) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        print("Conectó OK ->", cur.fetchone()[0])
