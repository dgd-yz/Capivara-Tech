from django.test import TestCase, override_settings
from django.urls import reverse

from certification.models import Certificate
from core.event_config import get_event_config


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CertificateLookupTests(TestCase):
    def make(self, email, activity, workload=24):
        return Certificate.objects.create(
            participant_name="Maria da Silva", participant_email=email, activity=activity,
            workload=workload, location="São Raimundo Nonato",
            certifier_name="Fulano", certifier_position="Coordenador", text="<p>texto</p>",
        )

    def search(self, email):
        return self.client.post(reverse("certificates"), {"email": email})

    def test_finds_certificates_ignoring_case_and_spaces(self):
        event = get_event_config()["name"]
        workshop = self.make("Maria@Gmail.com", "Django Girls: Introdução a Desenvolvimento Web", 8)
        general = self.make("Maria@Gmail.com", event)
        self.make("outra@gmail.com", event)

        response = self.search("  maria@gmail.COM ")

        self.assertContains(response, "2 certificados para maria@gmail.COM")
        self.assertContains(response, f"Certificado: {event} (24 horas)")
        # Nome completo do minicurso, sem cortar em 20 caracteres.
        self.assertContains(response, "Certificado: Django Girls: Introdução a Desenvolvimento Web (8 horas)")
        self.assertEqual(list(response.context["certificates"]), [general, workshop])
        self.assertNotContains(response, "Nenhum certificado encontrado")

    def test_tells_when_nothing_is_found(self):
        self.make("maria@gmail.com", get_event_config()["name"])

        response = self.search("ninguem@gmail.com")

        self.assertContains(response, "Nenhum certificado encontrado para <strong>ninguem@gmail.com</strong>")
        self.assertContains(response, get_event_config()["contact_email"])
        self.assertNotContains(response, "Certificados Encontrados")

    def test_invalid_email_shows_form_error_without_message(self):
        response = self.search("isso-nao-e-email")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Nenhum certificado encontrado")
        self.assertTrue(response.context["cf"].errors)

    def test_get_shows_only_the_form(self):
        response = self.client.get(reverse("certificates"))

        self.assertContains(response, "Procurar Certificados")
        self.assertNotContains(response, "Nenhum certificado encontrado")
