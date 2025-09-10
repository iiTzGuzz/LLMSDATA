# src/api/urls.py
from django.urls import path
from .views import (
    ProcesarArchivoUploadView,
    ProcesarArchivoPathView,
    UltimosRegistrosView,
    ConsultaLLMView,
)

# 👇 añade estas importaciones
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("procesar-archivo/upload/", ProcesarArchivoUploadView.as_view(), name="procesar_archivo_upload"),
    path("procesar-archivo/", ProcesarArchivoPathView.as_view(), name="procesar_archivo_path"),
    path("registros/ultimos/", UltimosRegistrosView.as_view(), name="ultimos_registros"),
    path("consulta-llm/", ConsultaLLMView.as_view(), name="consulta_llm"),

    # 👇 SIN el prefijo "api/"
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
