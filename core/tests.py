from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django_tasks.backends.database.models import DBTaskResult

from core.admin import RegistrationAdmin
from core.models import EmailSettings, Registration
from core.tasks import send_email, send_registration_email


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Capivara Tech <evento@example.com>",
    TASKS={"default": {"BACKEND": "django_tasks.backends.database.DatabaseBackend", "QUEUES": ["default", "pictures"]}},
)
class RegistrationEmailTests(TestCase):
    def setUp(self):
        self.participant = Registration.objects.create(full_name="Ana Silva", email="ana@example.com")
        self.configuration = EmailSettings.get_solo()
        self.model_admin = RegistrationAdmin(Registration, AdminSite())

    def test_registration_queues_receipt_without_confirming(self):
        response = self.client.post(reverse("registration"), {
            "full_name": "Maria", "email": "maria@example.com",
            "activity": "ORIGIN", "workshop": "0",
        })
        self.assertEqual(response.status_code, 302)
        participant = Registration.objects.get(email="maria@example.com")
        self.assertFalse(participant.confirmated)
        result = DBTaskResult.objects.get(task_path="core.tasks.send_registration_email")
        self.assertEqual(result.args_kwargs, {"args": [participant.pk, "received"], "kwargs": {}})
        send_registration_email.call(*result.args_kwargs["args"])
        self.assertEqual(mail.outbox[0].to, [participant.email])
        self.assertIn("Recebemos sua inscrição", mail.outbox[0].body)

    def test_registration_rolls_back_if_queue_fails(self):
        with patch("core.views.send_registration_email") as task:
            task.enqueue.side_effect = RuntimeError("queue unavailable")
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("registration"), {
                    "full_name": "Maria", "email": "maria@example.com",
                    "activity": "ORIGIN", "workshop": "0",
                })
        self.assertFalse(Registration.objects.filter(email="maria@example.com").exists())

    def test_custom_message_and_placeholders(self):
        self.configuration.received_subject = "Olá ${nome}"
        self.configuration.received_body = "${email}\n${minicurso}\n${protocolo}\nAté breve!"
        self.configuration.save()
        send_registration_email.call(self.participant.pk)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Olá Ana Silva")
        self.assertIn("Não participarei de minicurso", message.body)
        self.assertIn(str(self.participant.uuid), message.body)
        self.assertEqual(message.from_email, "Capivara Tech <evento@example.com>")

    def test_invalid_placeholders_and_multiline_subject_rejected(self):
        for field, value in [("received_body", "Olá ${naome}"), ("received_body", "Olá ${nome"), ("received_subject", "Olá\nBcc: outro@example.com")]:
            with self.subTest(field=field, value=value):
                configuration = EmailSettings(**{field: value})
                with self.assertRaises(ValidationError):
                    configuration.full_clean()

    def test_confirm_action_only_queues_new_confirmations(self):
        queryset = Registration.objects.filter(pk=self.participant.pk)
        with patch.object(self.model_admin, "message_user"):
            self.model_admin.confirm_registration(None, queryset)
            self.model_admin.confirm_registration(None, queryset)
        self.participant.refresh_from_db()
        self.assertTrue(self.participant.confirmated)
        self.assertEqual(DBTaskResult.objects.count(), 1)
        send_registration_email.call(self.participant.pk, "confirmed")
        self.assertIn("foi confirmada", mail.outbox[0].body)

    def test_confirmation_checkbox_queues_email(self):
        self.participant.confirmated = True
        self.model_admin.save_model(None, self.participant, None, True)
        self.assertEqual(DBTaskResult.objects.get().args_kwargs["args"], [self.participant.pk, "confirmed"])

    def test_revoked_confirmation_is_not_sent(self):
        send_registration_email.call(self.participant.pk, "confirmed")
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_uses_current_status(self):
        confirmed = Registration.objects.create(full_name="Bia", email="bia@example.com", confirmated=True)
        with patch.object(self.model_admin, "message_user"):
            self.model_admin.resend_registration_email(None, Registration.objects.all())
        arguments = [row.args_kwargs["args"] for row in DBTaskResult.objects.all()]
        self.assertCountEqual(arguments, [[self.participant.pk, "received"], [confirmed.pk, "confirmed"]])

    def test_contact_uses_verified_sender_and_visitor_reply_to(self):
        self.configuration.contact_recipient = "contato@example.com"
        self.configuration.save()
        response = self.client.post(reverse("contact"), {
            "sender_name": "Visitante", "sender_email": "visitante@example.com",
            "subject": "Dúvida", "message": "Olá!",
        })
        self.assertEqual(response.status_code, 302)
        result = DBTaskResult.objects.get(task_path="core.tasks.send_email")
        send_email.call(*result.args_kwargs["args"])
        message = mail.outbox[0]
        self.assertEqual(message.from_email, "Capivara Tech <evento@example.com>")
        self.assertEqual(message.reply_to, ["visitante@example.com"])
        self.assertEqual(message.to, ["contato@example.com"])
        self.assertIn("Visitante", message.body)

    def test_existing_contact_tasks_keep_explicit_destination(self):
        send_email.call("Olá", "Mensagem", "Ana", "ana@example.com", "destino@example.com")
        self.assertEqual(mail.outbox[0].to, ["destino@example.com"])

    def test_contact_with_empty_setting_uses_contact_mailbox(self):
        self.configuration.contact_recipient = ""
        self.configuration.save()
        send_email.call("Olá", "Mensagem", "Ana", "ana@example.com")
        message = mail.outbox[0]
        self.assertEqual(message.to, ["contato@sistemasparainternet.com"])
        self.assertRegex(str(message.message()["Message-ID"]), r"^<[^<>]+@[^<>]+>$")
