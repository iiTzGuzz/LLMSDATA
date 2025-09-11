from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import MagicMock, patch

class LLMViewTests(TestCase):
    def test_llm_ok(self):
        client = APIClient()

        fake_agent = MagicMock()
        fake_agent.invoke.return_value = {"ok": True, "rows": [{"id": 1}]}

        with patch("api.views.get_agent", return_value=fake_agent):
            r = client.post("/api/consulta-llm/", {"instruccion": "Dame los clientes"}, format="json")

        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["ok"])
        self.assertIn("output", r.data)

    def test_llm_falta_instruccion(self):
        client = APIClient()
        r = client.post("/api/consulta-llm/", {}, format="json")
        self.assertEqual(r.status_code, 400)
