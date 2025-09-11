from django.test import TestCase
from rest_framework.test import APIClient
from api.models import Registro

class UltimosViewTests(TestCase):
    def test_ultimos_ok(self):
        Registro.objects.create(nombre="A", documento="1")
        Registro.objects.create(nombre="B", documento="2")

        client = APIClient()
        r = client.get("/api/registros/ultimos/?limit=2")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["ok"])
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data["rows"]), 2)
