from smtplib import SMTPAuthenticationError
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django_tasks.backends.database.management.commands.db_worker import Worker
from django_tasks.backends.database.models import DBTaskResult

from core.models import EmailDelivery, Registration
from core.tasks import send_email, send_registration_email
from core.email_tracking import current_task_id
from extra_settings.models import Setting


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    # O CI executa os testes antes do collectstatic. O admin não deve depender
    # de um manifest local que ainda não existe em um checkout limpo.
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class DeliveryTests(TestCase):
    def setUp(self):
        self.person = Registration.objects.create(full_name="Ana & Silva", email="ana@example.com", confirmated=True)
        setting = Setting.objects.get(name="EVENT_SITE_URL")
        setting.value = "https://evento.example/"
        setting.save()
        self.addCleanup(current_task_id.set, None)

    def run_task(self, result):
        worker = Worker(queue_names=["default"], interval=0, batch=True, backend_name="default", startup_delay=False, max_tasks=1, worker_id="test-email")
        worker.run_task(DBTaskResult.objects.get(pk=result.id))
        return DBTaskResult.objects.get(pk=result.id)

    def test_confirmed_banner_is_related_to_html_and_plain_text_is_preserved(self):
        result = send_registration_email.call(self.person.pk, "confirmed")
        mime = mail.outbox[0].message()
        self.assertEqual(mime.get_content_type(), "multipart/alternative")
        self.assertIn("Ana & Silva", mime.get_body(("plain",)).get_content())
        self.assertIn("https://evento.example/", mime.get_body(("plain",)).get_content())
        self.assertIn("cid:registration-banner", mime.get_body(("html",)).get_content())
        image = next(part for part in mime.walk() if part.get_content_type() == "image/png")
        self.assertEqual(image["Content-ID"], "<registration-banner>")
        self.assertGreater(len(image.get_payload(decode=True)), 1000)
        self.assertEqual(result["destinatarios"], ["ana@example.com"])

    def test_worker_saves_snapshot_link_and_result(self):
        task = self.run_task(send_registration_email.enqueue(self.person.pk, "confirmed"))
        self.assertEqual(task.status, "SUCCEEDED")
        delivery = task.email_deliveries.get()
        self.assertEqual(delivery.status, "sent")
        self.assertEqual(task.return_value["historico_email_id"], delivery.pk)
        self.person.email = "changed@example.com"
        self.person.save()
        delivery.refresh_from_db()
        self.assertEqual(delivery.recipients, ["ana@example.com"])
        self.assertIsNone(current_task_id.get())

    def test_smtp_failure_preserves_support_message_and_task_failure(self):
        result = send_email.enqueue("Preciso de ajuda", "Não consigo acessar.\nMeu protocolo é 123.", "Ana", "ana@example.com")
        with patch("django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=SMTPAuthenticationError(535, b"Authentication failed")):
            with self.assertLogs("django_tasks", level="ERROR") as logs:
                task = self.run_task(result)
        self.assertIn("SMTPAuthenticationError", "\n".join(logs.output))
        self.assertEqual(task.status, "FAILED")
        delivery = task.email_deliveries.get()
        self.assertEqual(delivery.status, "failed")
        self.assertIn("Meu protocolo é 123.", delivery.body)
        self.assertIn("SMTPAuthenticationError", delivery.error)
        self.assertEqual(delivery.reply_to, ["ana@example.com"])

    def test_support_message_visible_before_execution_and_escaped(self):
        user = get_user_model().objects.create_superuser("admin-email", password="test")
        self.client.force_login(user)
        result = send_email.enqueue("Ajuda", "<script>alert(1)</script>\nDetalhes", "Ana", "ana@example.com")
        response = self.client.get(f"/admin/django_tasks_database/dbtaskresult/{result.id}/change/")
        self.assertContains(response, "ana@example.com")
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_task_admin_shows_history_after_delivery(self):
        user = get_user_model().objects.create_superuser("admin-history", password="test")
        self.client.force_login(user)
        task = self.run_task(send_email.enqueue("Assunto detalhado", "Minha mensagem completa", "Ana", "ana@example.com"))
        response = self.client.get(f"/admin/django_tasks_database/dbtaskresult/{task.pk}/change/")
        self.assertContains(response, "Minha mensagem completa")
        self.assertContains(response, "contato@sistemasparainternet.com")
        self.assertContains(self.client.get("/admin/core/emaildelivery/"), "Assunto detalhado")
