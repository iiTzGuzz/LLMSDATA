# src/api/views.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import mimetypes
from time import time as _now

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils.http import http_date

from rest_framework import status, serializers, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    inline_serializer,
)

from .models import Registro
from .services import procesar_archivo_y_guardar
from .llm_agent import get_agent  # 👈 getter lazy
from app.parser import normalize_filename


# --------------------------
# Helpers
# --------------------------
def _upload_dir() -> Path:
    upload_dir = Path(getattr(settings, "UPLOAD_DIR", "/app/data/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _serialize_registro(r: Registro) -> Dict[str, Any]:
    return {
        "id": r.id,
        "tipo_documento": r.tipo_documento,
        "documento": r.documento,
        "nombre": r.nombre,
        "producto": r.producto,
        "poliza": r.poliza,
        "periodo": r.periodo,
        "valor_asegurado": str(r.valor_asegurado) if r.valor_asegurado is not None else None,
        "valor_prima": str(r.valor_prima) if r.valor_prima is not None else None,
        "doc_cobro": r.doc_cobro,
        "fecha_ini": r.fecha_ini.isoformat() if r.fecha_ini else None,
        "fecha_fin": r.fecha_fin.isoformat() if r.fecha_fin else None,
        "dias": r.dias,
        "telefono_1": r.telefono_1,
        "telefono_2": r.telefono_2,
        "telefono_3": r.telefono_3,
        "ciudad": r.ciudad,
        "departamento": r.departamento,
        "fecha_venta": r.fecha_venta.isoformat() if r.fecha_venta else None,
        "fecha_nacimiento": r.fecha_nacimiento.isoformat() if r.fecha_nacimiento else None,
        "tipo_trans": r.tipo_trans,
        "beneficiarios": r.beneficiarios,
        "genero": r.genero,
        "sucursal": r.sucursal,
        "tipo_cuenta": r.tipo_cuenta,
        "ultimos_digitos_cuenta": r.ultimos_digitos_cuenta,
        "entidad_bancaria": r.entidad_bancaria,
        "nombre_banco": r.nombre_banco,
        "estado_debito": r.estado_debito,
        "causal_rechazo": r.causal_rechazo,
        "codigo_canal": r.codigo_canal,
        "descripcion_canal": r.descripcion_canal,
        "codigo_estrategia": r.codigo_estrategia,
        "tipo_estrategia": r.tipo_estrategia,
        "correo_electronico": r.correo_electronico,
        "fecha_entrega_colmena": r.fecha_entrega_colmena.isoformat() if r.fecha_entrega_colmena else None,
        "mes_a_trabajar": r.mes_a_trabajar,
        "nombre_db": r.nombre_db,
        "telefono": bool(r.telefono),
        "whatsapp": bool(r.whatsapp),
        "texto": bool(r.texto),
        "email": bool(r.email),
        "fisica": bool(r.fisica),
        "mejor_canal": r.mejor_canal,
        "contactar_al": r.contactar_al,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# --------------------------
# Serializers para Swagger
# --------------------------
class ExportsSerializer(serializers.Serializer):
    json_path = serializers.CharField(required=False, allow_null=True)
    csv_path = serializers.CharField(required=False, allow_null=True)
    json_url = serializers.CharField(required=False, allow_null=True)
    csv_url = serializers.CharField(required=False, allow_null=True)


class UploadRequestSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="Archivo de ancho fijo.")
    fecha = serializers.CharField(
        required=False, help_text="YYYYMMDD (opcional, si el nombre no trae fecha)"
    )


class UploadResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    saved_as = serializers.CharField()
    insertados = serializers.IntegerField()
    exports = ExportsSerializer(required=False)


class PathRequestSerializer(serializers.Serializer):
    path = serializers.CharField(help_text="Ruta completa al archivo en disco.")
    fecha = serializers.CharField(required=False, help_text="YYYYMMDD (opcional)")
    original_name = serializers.CharField(required=False, help_text="Nombre original (opcional)")


class OkCountResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    insertados = serializers.IntegerField()
    exports = ExportsSerializer(required=False)


class UltimosRegistrosResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    count = serializers.IntegerField()
    rows = serializers.ListField(child=serializers.DictField())


class ConsultaLLMRequestSerializer(serializers.Serializer):
    instruccion = serializers.CharField(help_text="Instrucción en lenguaje natural.")


class ConsultaLLMResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    instruccion = serializers.CharField(required=False)
    output = serializers.DictField(required=False)


class FileMetaSerializer(serializers.Serializer):
    name = serializers.CharField()
    size = serializers.IntegerField()
    modified = serializers.CharField()
    download_url = serializers.CharField()


class ListExportsResponseSerializer(serializers.Serializer):
    ok = serializers.BooleanField()
    count = serializers.IntegerField()
    files = serializers.ListField(child=FileMetaSerializer())


# --------------------------
# Vistas
# --------------------------
class ProcesarArchivoUploadView(APIView):
    """
    Sube un archivo, normaliza el nombre a NOMBRE_YYYYMMDD.txt y procesa.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Procesamiento"],
        request={"multipart/form-data": UploadRequestSerializer},
        responses={
            201: UploadResponseSerializer,
            400: inline_serializer(name="ErrorResponse", fields={"detail": serializers.CharField()}),
        },
    )
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "Falta campo 'file'."}, status=status.HTTP_400_BAD_REQUEST)

        fecha: Optional[str] = request.data.get("fecha") or None
        if fecha and (len(fecha) != 8 or not fecha.isdigit()):
            return Response({"detail": "El campo 'fecha' debe ser YYYYMMDD."}, status=status.HTTP_400_BAD_REQUEST)

        upload_dir = _upload_dir()
        try:
            normalized_name = normalize_filename(file_obj.name, fecha)
        except Exception as e:
            return Response({"detail": f"Error normalizando nombre: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        dest_path = upload_dir / normalized_name
        with dest_path.open("wb+") as dst:
            for chunk in file_obj.chunks():
                dst.write(chunk)

        try:
            insertados = procesar_archivo_y_guardar(
                str(dest_path),
                yyyymmdd_override=fecha,
                original_name=file_obj.name,
            )
        except Exception as e:
            return Response({"detail": f"Error procesando archivo: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        outs = getattr(procesar_archivo_y_guardar, "_last_outputs", {})
        return Response(
            {"ok": True, "saved_as": str(dest_path), "insertados": insertados, "exports": outs},
            status=status.HTTP_201_CREATED,
        )


class ProcesarArchivoPathView(APIView):
    """
    Procesa un archivo existente en disco (por ruta).
    """
    parser_classes = (JSONParser,)
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Procesamiento"],
        request=PathRequestSerializer,
        responses={200: OkCountResponseSerializer},
        examples=[
            OpenApiExample(
                "Procesar por ruta",
                value={"path": "/app/data/PRUEBA_20250529.txt", "fecha": "20250529", "original_name": "clientes.txt"},
                request_only=True,
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        path: Optional[str] = request.data.get("path")
        if not path:
            return Response({"detail": "Falta 'path'."}, status=status.HTTP_400_BAD_REQUEST)

        fecha: Optional[str] = request.data.get("fecha")
        if fecha and (len(fecha) != 8 or not fecha.isdigit()):
            return Response({"detail": "El campo 'fecha' debe ser YYYYMMDD."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            insertados = procesar_archivo_y_guardar(
                path, yyyymmdd_override=fecha, original_name=request.data.get("original_name")
            )
        except Exception as e:
            return Response({"detail": f"Error procesando archivo: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        outs = getattr(procesar_archivo_y_guardar, "_last_outputs", {})
        return Response({"ok": True, "insertados": insertados, "exports": outs}, status=status.HTTP_200_OK)


class UltimosRegistrosView(APIView):
    """
    Devuelve los últimos N registros insertados.
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Consultas"],
        parameters=[
            OpenApiParameter(name="limit", description="Cantidad de filas (1–500). Default 50.",
                             required=False, type=int, location=OpenApiParameter.QUERY),
        ],
        responses={200: UltimosRegistrosResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        try:
            limit = int(request.query_params.get("limit", 50))
        except ValueError:
            limit = 50
        limit = max(1, min(limit, 500))

        registros = Registro.objects.order_by("-id")[:limit]
        data = [_serialize_registro(r) for r in registros]
        return Response({"ok": True, "count": len(data), "rows": data}, status=status.HTTP_200_OK)


class ConsultaLLMView(APIView):
    """
    Pide al agente (LangChain) que procese una instrucción en lenguaje natural.
    """
    parser_classes = (JSONParser,)
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Consultas"],
        request=ConsultaLLMRequestSerializer,
        responses={200: ConsultaLLMResponseSerializer},
        examples=[
            OpenApiExample(
                "Ejemplo: menores de edad",
                value={"instruccion": "Muéstrame los menores de 18: nombre y teléfono."},
                request_only=True,
            ),
            OpenApiExample(
                "Ejemplo: top por prima",
                value={"instruccion": "Top 10 por valor_prima con nombre, póliza y valor_prima."},
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        instr: Optional[str] = request.data.get("instruccion")
        if not instr or not isinstance(instr, str):
            return Response({"detail": "Falta 'instruccion' (string)."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = get_agent().invoke({"instruccion": instr})
        except Exception as e:
            return Response({"ok": False, "detail": f"Error ejecutando el agente: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(result, str):
            payload: Dict[str, Any] = {"ok": True, "instruccion": instr, "output": {"text": result}}
        elif isinstance(result, dict):
            payload = {"ok": True, "instruccion": instr, "output": result}
        else:
            payload = {"ok": True, "instruccion": instr, "output": {"result": str(result)}}

        return Response(payload, status=status.HTTP_200_OK)


class ListarExportsView(APIView):
    """
    Lista los archivos exportados (CSV/JSON) disponibles para descarga.
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Exports"],
        responses={200: ListExportsResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        out_dir = Path(settings.EXPORT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for p in sorted(out_dir.glob("*")):
            if p.is_file():
                stat = p.stat()
                files.append({
                    "name": p.name,
                    "size": stat.st_size,
                    "modified": http_date(stat.st_mtime),
                    "download_url": request.build_absolute_uri(
                        f"/api/exports/descargar/{p.name}"
                    ),
                })
        return Response({"ok": True, "count": len(files), "files": files}, status=200)


class DescargarExportView(APIView):
    """
    Descarga un archivo exportado por nombre.
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        tags=["Exports"],
        parameters=[OpenApiParameter(name="filename", required=True, type=str, location=OpenApiParameter.PATH)],
        responses={200: {"content": {"application/octet-stream": {}}}},
    )
    def get(self, request, filename: str, *args, **kwargs):
        safe = Path(filename).name  # evita path traversal
        p = Path(settings.EXPORT_DIR) / safe
        if not p.exists() or not p.is_file():
            raise Http404("Archivo no encontrado")

        ctype, _ = mimetypes.guess_type(p.name)
        resp = FileResponse(
            p.open("rb"),
            as_attachment=True,
            filename=p.name,
            content_type=ctype or "application/octet-stream",
        )
        resp["Last-Modified"] = http_date(p.stat().st_mtime)
        resp["Cache-Control"] = "no-store"
        resp["X-Generated-At"] = http_date(_now())
        return resp
