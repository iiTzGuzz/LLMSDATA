# SData – Backend (Django + DRF)

Backend para cargar archivos de **ancho fijo**, normalizarlos, **insertar en PostgreSQL**, exportar **CSV/JSON**, y consultar con un **agente LLM**. Incluye **Swagger UI** con `drf-spectacular`.

---

## 🧱 Stack

- **Python 3.12+ / 3.13+**
- **Django 5**
- **Django REST Framework (DRF)**
- **PostgreSQL** (local y Railway)
- **psycopg 3**
- **LangChain + OpenAI** (para el agente)
- **drf-spectacular** + **sidecar** (Swagger UI sin CDN)
- **Gunicorn + WhiteNoise** (producción)
- **Docker / Docker Compose** (opcional)

---

## 📁 Estructura mínima del proyecto

```
.
├─ src/
│  ├─ backend/
│  │  ├─ settings.py
│  │  ├─ urls.py
│  │  └─ wsgi.py
│  ├─ api/
│  │  ├─ models.py
│  │  ├─ views.py
│  │  ├─ urls.py
│  │  ├─ services.py
│  │  └─ llm_agent.py
│  ├─ app/
│  │  ├─ parser.py            # FixedWidthParser + normalize_filename
│  │  ├─ transformers.py      # BusinessTransformer
│  │  └─ constants.py         # COLUMNS_DB, etc.
│  └─ manage.py
├─ requirements.txt
├─ entrypoint.sh              # (si usas Docker)
└─ .env                       # variables de entorno
```

---

## ⚙️ Variables de entorno (.env)

Crea un archivo **`.env`** en la raíz del repo (junto a `requirements.txt`).

### 1) Local con PostgreSQL local
```env
# Django
DEBUG=True
SECRET_KEY=django-insecure-key
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,[::1]

# PostgreSQL (local)
POSTGRES_DB=prueba_db
POSTGRES_USER=prueba_user
POSTGRES_PASSWORD=prueba_pass
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_SSLMODE=prefer      # prefer|disable para local

# OpenAI (LLM)
OPENAI_API_KEY=TU_API_KEY

# Media y directorios de trabajo
MEDIA_ROOT=./src/media
UPLOAD_DIR=./src/media/uploads
EXPORT_DIR=./src/media/outputs
```

### 2) Local con base de datos **Railway**
```env
DEBUG=True
SECRET_KEY=django-insecure-key
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,[::1]

# Railway Postgres (reemplaza con tus valores reales)
POSTGRES_DB=railway
POSTGRES_USER=postgres
POSTGRES_PASSWORD=************
POSTGRES_HOST=yamanote.proxy.rlwy.net
POSTGRES_PORT=47085
POSTGRES_SSLMODE=require      # Railway requiere SSL

OPENAI_API_KEY=TU_API_KEY

MEDIA_ROOT=./src/media
UPLOAD_DIR=./src/media/uploads
EXPORT_DIR=./src/media/outputs
```

### 3) Producción (Railway – servicio web)
```env
DEBUG=False
SECRET_KEY=pon-una-clave-larga-super-secreta
DJANGO_ALLOWED_HOSTS=llmsdata-production.up.railway.app

# DB Railway (usa los valores del add-on)
POSTGRES_DB=railway
POSTGRES_USER=postgres
POSTGRES_PASSWORD=************
POSTGRES_HOST=yamanote.proxy.rlwy.net
POSTGRES_PORT=47085
POSTGRES_SSLMODE=require

OPENAI_API_KEY=TU_API_KEY

# Paths dentro del contenedor (persisten mientras viva el container)
MEDIA_ROOT=/app/src/media
UPLOAD_DIR=/app/data/uploads
EXPORT_DIR=/app/data/exports
```

> **Notas**
> - `POSTGRES_SSLMODE`: usa `prefer/disable` local; **`require`** en Railway.
> - `DJANGO_ALLOWED_HOSTS`: incluye el dominio público de tu servicio.
> - `OPENAI_API_KEY` solo es necesario si vas a usar `/api/consulta-llm/`.

---

## 🔧 Instalación local (sin Docker)

1) Crear y activar entorno virtual
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
```

2) Instalar dependencias
```bash
pip install -r requirements.txt
```

3) Exportar variables (ya en `.env`), preparar BD y correr migraciones
```bash
cd src
python manage.py migrate
```

4) Iniciar servidor
```bash
python manage.py runserver 8000
```
Abre: `http://127.0.0.1:8000/`

---

## 📚 Documentación (Swagger / ReDoc)

Rutas (ya montadas bajo `/api/`):
- **OpenAPI JSON**: `GET /api/schema/`
- **Swagger UI**: `[GET /api/schema/swagger-ui/](https://llmsdata-production.up.railway.app/api/schema/swagger-ui/#/)`
- **ReDoc**: `GET /api/schema/redoc/`

> Si en producción no carga el CSS/JS del Swagger, asegúrate de:
> - Tener **`drf-spectacular-sidecar`** instalado.
> - Haber ejecutado `python manage.py collectstatic --noinput`.
> - Tener **WhiteNoise** configurado en `MIDDLEWARE` y `STATIC_ROOT` poblado.

---

## 🧪 Endpoints principales

### 1) Subir y procesar archivo
`POST /api/procesar-archivo/upload/` (multipart/form-data)

**Campos:**
- `file`: archivo de ancho fijo (obligatorio)
- `fecha`: `YYYYMMDD` (opcional, si el nombre no trae fecha)

**cURL:**
```bash
curl -X POST http://127.0.0.1:8000/api/procesar-archivo/upload/ \
  -H "Accept: application/json" \
  -F "file=@C:/ruta/a/TU_ARCHIVO_20250115.txt" \
  -F "fecha=20250115"
```

**Respuesta 201:**
```json
{
  "ok": true,
  "saved_as": "/app/data/uploads/TU_ARCHIVO_20250115.txt",
  "insertados": 123
}
```

### 2) Procesar por ruta (archivo ya en disco)
`POST /api/procesar-archivo/` (JSON)

**Body:**
```json
{
  "path": "/app/data/uploads/TU_ARCHIVO_20250115.txt",
  "fecha": "20250115",
  "original_name": "archivo_original.txt"
}
```

**cURL:**
```bash
curl -X POST http://127.0.0.1:8000/api/procesar-archivo/ \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{ "path": "/app/data/uploads/TU_ARCHIVO_20250115.txt", "fecha":"20250115", "original_name": "archivo_original.txt" }'
```

**Respuesta 200:**
```json
{"ok": true, "insertados": 123}
```

### 3) Últimos registros
`GET /api/registros/ultimos/?limit=50`

**cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/api/registros/ultimos/?limit=5" -H "Accept: application/json"
```

**Respuesta 200 (ejemplo):**
```json
{
  "ok": true,
  "count": 5,
  "rows": [
    {"id": 10, "nombre": "JUAN PEREZ", "...": "..."}
  ]
}
```

### 4) Consulta LLM (lenguaje natural → SQL seguro / herramientas)
`POST /api/consulta-llm/` (JSON)

**Body:**
```json
{"instruccion": "Dame los 10 clientes con mayor valor_prima, con nombre y póliza"}
```

**cURL:**
```bash
curl -X POST http://127.0.0.1:8000/api/consulta-llm/ \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"instruccion":"Dame los 10 clientes con mayor valor_prima, con nombre y póliza"}'
```

**Respuesta 200 (ejemplo):**
```json
{
  "ok": true,
  "instruccion": "Dame los 10 ...",
  "output": {
    "ok": true,
    "sql": "SELECT ... LIMIT 10;",
    "rows": [ ... ],
    "row_count": 10
  }
}
```

---

## 📦 Dónde se guardan los archivos (uploads y exports)

- **Uploads**: `UPLOAD_DIR` (por defecto `./src/media/uploads` en local, `/app/data/uploads` en contenedor).
- **Exports (CSV/JSON)**: `EXPORT_DIR` (por defecto `./src/media/outputs` en local, `/app/data/exports` en contenedor).  
  El servicio también devuelve **URLs públicas** bajo `MEDIA_URL` (p.ej., `/media/outputs/archivo.csv`).

> **Railway**: el sistema de archivos es **efímero**. Los archivos se pierden al redeploy. Guarda en S3/GCS si requieres persistencia.

---

## 🐳 Docker / Docker Compose (opcional)

**docker-compose.yml** (ejemplo):
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  web:
    build: .
    env_file: .env
    volumes:
      - ./src:/app/src
      - ./data:/app/data
    ports:
      - "8000:8000"
    depends_on:
      - db
    command: ["/bin/sh", "-lc", "bash entrypoint.sh"]

volumes:
  pgdata: {}
```

**entrypoint.sh** (simple y apto para dev):
```bash
#!/usr/bin/env bash
set -e

echo "Esperando a Postgres en $POSTGRES_HOST:$POSTGRES_PORT ..."
until nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 1
done
echo "Postgres listo."

python /app/src/manage.py migrate --noinput

# Crea carpetas locales para media
mkdir -p /app/src/media/uploads /app/src/media/outputs /app/data/uploads /app/data/exports

# Servidor dev (usa gunicorn en prod/Railway)
python /app/src/manage.py runserver 0.0.0.0:8000
```

**Levantar:**
```bash
docker compose up --build
```

---

## 🚀 Despliegue en Railway (producción)

1. Crea el servicio **Web** y el add-on **PostgreSQL** (Railway).
2. En **Variables** agrega todo lo de `.env` de producción (ver arriba).
3. **Start Command** del servicio web:
   ```bash
   bash -lc "python /app/src/manage.py collectstatic --noinput && gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT"
   ```
4. Asegúrate de tener:
   - `whitenoise` instalado y configurado en `MIDDLEWARE` (ver sección siguiente).
   - `drf-spectacular-sidecar` instalado.
   - `DEBUG=False` y `DJANGO_ALLOWED_HOSTS` con tu dominio Railway.

### WhiteNoise (estáticos en prod)
En `settings.py`:
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # <= después de Security
    # ...
]
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_MAX_AGE = 31536000  # cache 1 año
```

Luego en Railway el `collectstatic` del start command dejará todo servido.

---

## 🧪 Pruebas unitarias

Ejecutar:
```bash
cd src
python manage.py test
```

**Si aparece** `Got an error creating the test database: permission denied to create database`:

Opción A – darle permiso al usuario para crear DB de tests:
```sql
-- Conecta como superusuario y ejecuta:
ALTER USER prueba_user CREATEDB;
```

Opción B – usar otra base específica de tests (en `settings.py` o `.env`):
```python
# settings.py (opcional)
DATABASES["default"]["TEST"] = {"NAME": "prueba_db_test"}
```
y crea esa DB manualmente con tu superusuario.

Opción C – usa SQLite para tests (rápido y sin permisos), por ejemplo con una variable:
```env
TEST_WITH_SQLITE=True
```
y en `settings.py` algo como:
```python
if os.getenv("TEST_WITH_SQLITE", "False").lower() in ("true","1","t"):
    DATABASES["default"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
```

---

## ❗ Troubleshooting (errores comunes)

- **`DisallowedHost: Invalid HTTP_HOST header '127.0.0.1:8000'`**  
  Agrega `127.0.0.1` a `DJANGO_ALLOWED_HOSTS`.

- **`400 Bad Request` al subir archivo**  
  Asegúrate de usar `multipart/form-data` y el campo **`file`** (no JSON).

- **`404 /api/upload`**  
  La ruta correcta es `/api/procesar-archivo/upload/`.

- **`psycopg.OperationalError: getaddrinfo failed`**  
  Revisa `POSTGRES_HOST` (sin dos puntos al final), y que el host resuelva.

- **`server does not support SSL, but SSL was required`**  
  En local usa `POSTGRES_SSLMODE=prefer` o `disable`. En Railway **`require`**.

- **`password authentication failed`**  
  Credenciales incorrectas o DB/usuario no coincide.

- **Swagger sin CSS/JS (Not Found)**  
  Instala `drf-spectacular-sidecar`, ejecuta `collectstatic`, y configura WhiteNoise.

- **En Railway no veo archivos**  
  Revisa directorios:
  - Uploads: `${UPLOAD_DIR:-/app/data/uploads}`
  - Exports: `${EXPORT_DIR:-/app/data/exports}`  
  Los archivos existen **mientras vive el container**. Para persistencia real usa S3/GCS.

---

## 🧰 Dependencias clave (requirements)

Asegúrate de incluir (ya provisto en `requirements.txt`):
```
Django==5.2.6
djangorestframework==3.15.2
psycopg[binary]>=3.1,<4
python-dotenv==1.0.1
openai>=1.40.0
langchain>=0.2.12
langchain-community>=0.2.10
langchain-openai>=0.2.0
tiktoken>=0.7.0
drf-spectacular>=0.27.2
drf-spectacular-sidecar>=2024.7.1
gunicorn>=22.0.0
whitenoise>=6.7.0
Faker>=25.0.0
django-cors-headers>=4.4.0
```

---

## 🔌 Endpoints de salud / verificación (opcional)

Puedes agregar una vista simple para verificar que el servicio corre y la DB responde:
```python
# src/backend/urls.py
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection

def health(_):
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

urlpatterns = [
    path("api/", include("api.urls")),
    path("health/", health),
]
```

---

## ✅ Checklist rápido

- [ ] `.env` correcto (local / Railway)
- [ ] Migraciones: `python manage.py migrate`
- [ ] Swagger accesible: `/api/schema/swagger-ui/`
- [ ] Subida/Procesado funciona: `/api/procesar-archivo/upload/`
- [ ] Exports visibles: `/media/outputs/*.csv|*.json`
- [ ] Gunicorn + WhiteNoise en producción
- [ ] `POSTGRES_SSLMODE=require` en Railway

---

## 📝 Licencia

MIT (o la que prefieras).
