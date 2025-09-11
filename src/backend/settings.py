from pathlib import Path
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ========================
# BASE DIR
# ========================
BASE_DIR = Path(__file__).resolve().parent.parent

# ========================
# CONFIGURACIÓN BÁSICA
# ========================
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-secret-key")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

_raw_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,[::1]")
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(",") if h.strip()]

if DEBUG:
    for h in ("127.0.0.1", "localhost", "[::1]"):
        if h not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(h)

# CSRF: puedes agregar más orígenes por env: DJANGO_CSRF_TRUSTED_ORIGINS="https://tu-dominio,https://otro"
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
_raw_csrf = os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if _raw_csrf:
    CSRF_TRUSTED_ORIGINS += [u.strip() for u in _raw_csrf.split(",") if u.strip()]

# ========================
# APLICACIONES INSTALADAS
# ========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",          # API REST
    "api",                     # App propia

    "drf_spectacular",         # OpenAPI
    "drf_spectacular_sidecar", # Assets locales de Swagger/ReDoc
]

# ========================
# MIDDLEWARE
# ========================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise para servir estáticos (incluye sidecar) en prod
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ========================
# URLS / WSGI
# ========================
ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

# ========================
# BASE DE DATOS (PostgreSQL)
# ========================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            # Si no especificas, usamos "prefer" (local sin SSL y Railway con SSL ok)
            "sslmode": os.getenv("POSTGRES_SSLMODE", "prefer"),
        },
    }
}

# ========================
# AUTENTICACIÓN
# ========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ========================
# INTERNACIONALIZACIÓN
# ========================
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# ========================
# ARCHIVOS ESTÁTICOS
# ========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Evita el warning si no existe la carpeta "static"
STATICFILES_DIRS = [p for p in [BASE_DIR / "static"] if p.exists()]

# WhiteNoise: archivos comprimidos y versionados
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ========================
# MEDIA / Directorios de trabajo
# ========================
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))

# Directorios de trabajo (overrideables por env)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", MEDIA_ROOT / "uploads"))
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", MEDIA_ROOT / "exports"))

# ========================
# DRF CONFIG
# ========================
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",  # para upload
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",

    # Auth/Permisos (ajústalo si necesitas restringir)
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# ========================
# CONFIG. CLAVE PRIMARIA
# ========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ========================
# SPECTACULAR (OpenAPI/Swagger)
# ========================
SPECTACULAR_SETTINGS = {
    "TITLE": "SmartData – API",
    "DESCRIPTION": "ETL de archivo de ancho fijo, consulta por LLM y endpoints de consulta.",
    "VERSION": "1.0.0",
    "SERVERS": [
        {"url": "http://127.0.0.1:8000"},
        {"url": "http://localhost:8000"},
        {"url": "https://llmsdata-production.up.railway.app"},
    ],

    # Usar assets locales (evita CDN y resuelve 404 tras collectstatic)
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",

    # (opcional) Basic Auth visible en Swagger
    "SECURITY_SCHEMES": {"basicAuth": {"type": "http", "scheme": "basic"}},
    "SECURITY": [{"basicAuth": []}],
}
