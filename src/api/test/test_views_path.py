from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

class PathViewTests(TestCase):
    def test_path_ok(self):
        client = APIClient()
        with patch("api.views.procesar_archivo_y_guardar", return_value=3):
            r = client.post("/api/procesar-archivo/", {"path": "/app/data/X.txt", "fecha": "20250529"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["ok"], True)
        self.assertEqual(r.data["insertados"], 3)

    def test_path_sin_path(self):
        client = APIClient()
        r = client.post("/api/procesar-archivo/", {"fecha": "20250529"}, format="json")
        self.assertEqual(r.status_code, 400)
