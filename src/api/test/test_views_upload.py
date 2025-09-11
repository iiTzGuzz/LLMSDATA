from django.test import TestCase
from django.test.utils import override_settings
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from pathlib import Path
import tempfile


class UploadViewTests(TestCase):
    def test_upload_ok(self):
        client = APIClient()
        with tempfile.TemporaryDirectory() as tmp:
            media_root = Path(tmp) / "media"
            media_root.mkdir(parents=True, exist_ok=True)
            upload_dir = media_root / "uploads"

            file_content = b"hola mundo\n"
            upl = SimpleUploadedFile("MIARCHIVO.txt", file_content, content_type="text/plain")

            with override_settings(MEDIA_ROOT=str(media_root), UPLOAD_DIR=str(upload_dir)), \
                 patch("api.views.normalize_filename", return_value="NORMAL_20250529.txt"), \
                 patch("api.views.procesar_archivo_y_guardar", return_value=5):

                r = client.post("/api/procesar-archivo/upload/", {"file": upl, "fecha": "20250529"}, format="multipart")

            self.assertEqual(r.status_code, 201, r.content)
            self.assertTrue("saved_as" in r.data)
            # El archivo realmente se escribe en disco
            saved_path = Path(r.data["saved_as"])
            self.assertTrue(saved_path.exists())
            self.assertEqual(r.data["insertados"], 5)

    def test_upload_falta_file(self):
        client = APIClient()
        r = client.post("/api/procesar-archivo/upload/", {"fecha": "20250529"}, format="multipart")
        self.assertEqual(r.status_code, 400)
