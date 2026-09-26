import datetime
import shutil
import tempfile
from importlib import import_module
from io import BytesIO
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django_tasks.backends.database.models import DBTaskResult
from PIL import Image

from core.admin import RegistrationAdmin
from core.attendance import workshop_activity
from core.forms import RegistrationAdminForm, RegistrationForm
from core.models import (
    EmailSettings,
    EventDay,
    Registration,
    ScheduleItem,
    Speaker,
    Workshop,
    get_workshops_choices,
)
from core.tasks import send_email, send_registration_email

# O CI roda os testes antes do collectstatic, então não dá para depender do manifest.
PLAIN_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def make_image(size, fmt="PNG"):
    buffer = BytesIO()
    Image.new("RGB", size, (200, 120, 60)).save(buffer, fmt)
    return buffer.getvalue()


class SpeakerModelTests(TestCase):
    def test_label_joins_session_and_role(self):
        self.assertEqual(
            Speaker(name="A", session="Palestra 1", role="Dev").label,
            "Palestra 1 · Dev",
        )
        self.assertEqual(Speaker(name="A", session="Palestra 1").label, "Palestra 1")
        self.assertEqual(Speaker(name="A", role="Dev").label, "Dev")
        self.assertEqual(Speaker(name="A").label, "")

    def test_photo_is_resized_and_saved_as_jpeg(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        with override_settings(MEDIA_ROOT=media):
            speaker = Speaker.objects.create(
                name="Maria Souza",
                photo=SimpleUploadedFile("IMG_1.PNG", make_image((3000, 2000))),
            )
            self.assertTrue(speaker.photo.name.endswith(".jpg"))
            with Image.open(speaker.photo.path) as saved:
                self.assertEqual(saved.format, "JPEG")
                self.assertLessEqual(max(saved.size), 1000)


@override_settings(STORAGES=PLAIN_STORAGES)
class HomeSpeakersTests(TestCase):
    def setUp(self):
        # a migration de dados já cadastra os palestrantes atuais
        Speaker.objects.all().delete()

    def test_shows_only_published_speakers_in_order(self):
        Speaker.objects.create(name="Segunda Pessoa", order=20)
        Speaker.objects.create(name="Primeira Pessoa", order=10)
        Speaker.objects.create(name="Pessoa Oculta", order=5, published=False)

        html = self.client.get("/").content.decode()

        self.assertLess(html.index("Primeira Pessoa"), html.index("Segunda Pessoa"))
        self.assertNotIn("Pessoa Oculta", html)
        self.assertIn('data-count="2"', html)

    def test_renders_label_talk_and_paragraphs(self):
        Speaker.objects.create(
            name="Fulano",
            session="Palestra 2",
            role="Advogado",
            talk="Propriedade Intelectual",
            bio="Primeiro.\r\n\r\nSegundo.",
        )

        html = self.client.get("/").content.decode()

        self.assertIn('<div class="r">Palestra 2 · Advogado</div>', html)
        self.assertIn("“Propriedade Intelectual”<br><br>Primeiro.<br><br>Segundo.", html)

    def test_escapes_html_typed_in_the_admin(self):
        Speaker.objects.create(name="Fulano", bio="<script>alert(1)</script>")

        html = self.client.get("/").content.decode()

        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_hides_the_section_when_there_are_no_speakers(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('id="palestrantes"', response.content.decode())


@override_settings(STORAGES=PLAIN_STORAGES)
class SpeakerAdminTests(TestCase):
    def setUp(self):
        Speaker.objects.all().delete()
        self.admin = get_user_model().objects.create_superuser("admin-teste", password="x")
        self.client.force_login(self.admin)

    def test_admin_can_add_a_speaker(self):
        response = self.client.post(
            "/admin/core/speaker/add/",
            {
                "name": "Nova Pessoa",
                "session": "Minicurso 1",
                "role": "Django Girls",
                "talk": "",
                "bio": "Texto",
                "order": "10",
                "published": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Speaker.objects.get().label, "Minicurso 1 · Django Girls")

    def test_changelist_loads(self):
        Speaker.objects.create(name="Alguém")

        response = self.client.get("/admin/core/speaker/")

        self.assertContains(response, "Alguém")


def registration_data(**extra):
    data = {
        "activity": "ORIGIN",
        "full_name": "Maria José",
        "entity": "IFPI",
        "telephone": "",
        "email": "maria@example.com",
        "workshop": "0",
    }
    data.update(extra)
    return data


class WorkshopModelTests(TestCase):
    def setUp(self):
        Workshop.objects.all().delete()

    def test_labels_and_initials(self):
        w = Workshop(code="7", name="Git na Prática", instructors="João Dias")
        self.assertEqual(w.choice_label, "7. Git na Prática")
        self.assertEqual(w.title, "Minicurso 7 — Git na Prática")
        self.assertEqual(w.initials, "JD")
        self.assertEqual(Workshop(code="8", name="Django Girls").initials, "DG")

    def test_code_must_be_a_positive_number_without_zero(self):
        for bad in ("0", "abc", "01", "1a"):
            with self.assertRaises(ValidationError, msg=bad):
                Workshop(code=bad, name="X").full_clean()
        Workshop(code="12", name="X").full_clean()

    def test_seed_migration_has_the_original_workshops(self):
        seed = import_module(
            "core.migrations.0012_import_existing_workshops_and_schedule"
        )
        self.assertEqual(
            [(w["code"], w["name"]) for w in seed.WORKSHOPS],
            [
                ("1", "Django Girls"),
                ("2", "Teste de Software"),
                ("3", "Desenvolvimento de Games"),
            ],
        )

    def test_get_workshop_display_keeps_the_old_choice_labels(self):
        # usado pelo e-mail de inscrição (core/email_templates.py)
        Workshop.objects.create(code="1", name="Django Girls")
        self.assertEqual(
            Registration(workshop="1").get_workshop_display(), "1. Django Girls"
        )
        self.assertEqual(
            Registration(workshop="0").get_workshop_display(),
            "Não participarei de minicurso",
        )
        self.assertEqual(Registration(workshop="9").get_workshop_display(), "9")

    def test_get_workshop_name(self):
        Workshop.objects.create(code="1", name="Django Girls")
        self.assertEqual(Registration(workshop="1").get_workshop_name(), "Django Girls")
        with self.assertRaises(Workshop.DoesNotExist):
            Registration(workshop="9").get_workshop_name()


@override_settings(STORAGES=PLAIN_STORAGES)
class RegistrationWorkshopTests(TestCase):
    def setUp(self):
        Workshop.objects.all().delete()
        self.open = Workshop.objects.create(
            code="1", name="Aberto", capacity=2, order=1
        )
        self.hidden = Workshop.objects.create(
            code="2", name="Escondido", order=2, published=False
        )

    def codes(self):
        return [value for value, _ in get_workshops_choices()]

    def test_form_offers_none_plus_published_workshops(self):
        self.assertEqual(self.codes(), ["0", "1"])
        page = self.client.get("/inscrição")
        self.assertContains(page, "1. Aberto")
        self.assertNotContains(page, "Escondido")

    def test_full_workshop_disappears_from_the_form_and_is_rejected(self):
        for i in range(2):
            Registration.objects.create(
                **registration_data(email=f"a{i}@example.com", workshop="1")
            )

        self.assertEqual(self.codes(), ["0"])
        form = RegistrationForm(registration_data(email="c@example.com", workshop="1"))
        self.assertFalse(form.is_valid())

    def test_model_clean_rejects_full_and_unknown_codes_but_not_the_owner(self):
        first = Registration.objects.create(
            **registration_data(email="a@example.com", workshop="1")
        )
        Registration.objects.create(
            **registration_data(email="b@example.com", workshop="1")
        )

        first.clean()  # editar a própria inscrição não conta como vaga extra
        with self.assertRaises(ValidationError):
            Registration(
                **registration_data(email="c@example.com", workshop="1")
            ).clean()
        with self.assertRaises(ValidationError):
            Registration(**registration_data(workshop="99")).clean()
        Registration(**registration_data(workshop="0")).clean()

    def test_post_saves_the_code_untouched(self):
        response = self.client.post("/inscrição", registration_data(workshop="1"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Registration.objects.get().workshop, "1")

    def test_post_with_hidden_workshop_is_rejected(self):
        response = self.client.post("/inscrição", registration_data(workshop="2"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Registration.objects.exists())

    def test_admin_form_accepts_hidden_workshops_too(self):
        form = RegistrationAdminForm()
        self.assertIn("2", [value for value, _ in form.fields["workshop"].choices])

    def test_attendance_activity_comes_from_the_database(self):
        self.assertEqual(workshop_activity("0"), "Evento geral (sem minicurso)")
        self.assertEqual(workshop_activity("1"), "Aberto")
        self.assertEqual(workshop_activity("99"), "")


@override_settings(STORAGES=PLAIN_STORAGES)
class HomeWorkshopsTests(TestCase):
    def setUp(self):
        Workshop.objects.all().delete()

    def test_cards_come_from_the_database_in_order_and_hide_unpublished(self):
        Workshop.objects.create(
            code="2", name="Segundo", instructors="Ana Lima", order=2
        )
        Workshop.objects.create(
            code="1", name="Primeiro", instructors="Bia Souza", order=1
        )
        Workshop.objects.create(code="3", name="Oculto", order=3, published=False)

        html = self.client.get("/").content.decode()

        self.assertLess(
            html.index("Minicurso 1 — Primeiro"), html.index("Minicurso 2 — Segundo")
        )
        self.assertNotIn("Oculto", html)
        self.assertIn(
            '<span class="av">BS</span><span class="nm">Bia Souza</span>', html
        )

    def test_section_is_hidden_without_workshops(self):
        self.assertNotContains(self.client.get("/"), 'id="minicursos"')


@override_settings(STORAGES=PLAIN_STORAGES)
class ScheduleTests(TestCase):
    def setUp(self):
        EventDay.objects.all().delete()
        self.day1 = EventDay.objects.create(
            date=datetime.date(2026, 10, 21), subtitle="Minicursos"
        )
        self.day2 = EventDay.objects.create(
            date=datetime.date(2026, 10, 22), subtitle="Palestras & Cia"
        )

    def item(self, day, start, title, **kw):
        return ScheduleItem.objects.create(
            day=day, start_time=datetime.time.fromisoformat(start), title=title, **kw
        )

    def test_item_labels_and_tags(self):
        both = ScheduleItem(
            start_time=datetime.time(14), end_time=datetime.time(17, 30), tag="minicurso"
        )
        self.assertEqual(both.time_label, "14:00–17:30")
        self.assertEqual(ScheduleItem(start_time=datetime.time(9, 5)).time_label, "09:05")
        self.assertEqual(ScheduleItem(tag="abertura").tag_class, "pausa")
        self.assertEqual(ScheduleItem(tag="abertura").tag_text, "Abertura")
        self.assertEqual(ScheduleItem(tag="parceiro").tag_class, "cultura")

    def test_home_and_schedule_page_render_the_same_agenda(self):
        self.item(
            self.day1, "14:00", "Segundo", end_time=datetime.time(15), tag="palestra"
        )
        self.item(self.day1, "12:00", "Primeiro", subtitle="Lab 1", tag="abertura")
        self.item(self.day1, "13:00", "Oculto", published=False)

        for url in ("/", "/programação"):
            html = self.client.get(url).content.decode()
            self.assertLess(html.index("Primeiro"), html.index("Segundo"), url)
            self.assertNotIn("Oculto", html, url)
            self.assertIn("Dia 1 · 21/10", html, url)
            self.assertIn("Dia 2 · 22/10", html, url)
            self.assertIn("Palestras &amp; Cia", html, url)
            self.assertIn('<div class="who">Lab 1</div>', html, url)
            self.assertIn('<div class="ct-tag pausa">Abertura</div>', html, url)
            self.assertIn('<div class="time">14:00–15:00</div>', html, url)

    def test_unpublished_day_is_hidden_and_first_day_is_active(self):
        self.day2.published = False
        self.day2.save()

        html = self.client.get("/programação").content.decode()

        self.assertNotIn("Dia 2 ·", html)
        self.assertIn('class="ct-tab is-active" data-day="1"', html)
        self.assertIn('class="ct-day is-active" data-day="1"', html)

    def test_placeholder_when_there_are_no_days(self):
        EventDay.objects.all().delete()

        response = self.client.get("/programação")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "será divulgada em breve")


@override_settings(STORAGES=PLAIN_STORAGES)
class WorkshopScheduleAdminTests(TestCase):
    def setUp(self):
        Workshop.objects.all().delete()
        EventDay.objects.all().delete()
        self.admin = get_user_model().objects.create_superuser(
            "admin-teste2", password="x"
        )
        self.client.force_login(self.admin)

    def test_admin_can_add_a_workshop(self):
        response = self.client.post(
            "/admin/core/workshop/add/",
            {
                "code": "4",
                "name": "Novo",
                "instructors": "Fulano",
                "capacity": "20",
                "order": "40",
                "published": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Workshop.objects.get().capacity, 20)

    def test_code_is_read_only_after_creation(self):
        w = Workshop.objects.create(code="4", name="Novo")

        response = self.client.post(
            f"/admin/core/workshop/{w.pk}/change/",
            {
                "code": "9",
                "name": "Renomeado",
                "instructors": "",
                "capacity": "30",
                "order": "0",
                "published": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        w.refresh_from_db()
        self.assertEqual((w.code, w.name), ("4", "Renomeado"))

    def test_workshop_without_registrations_can_be_deleted(self):
        w = Workshop.objects.create(code="4", name="Novo")

        response = self.client.post(
            f"/admin/core/workshop/{w.pk}/delete/", {"post": "yes"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Workshop.objects.filter(pk=w.pk).exists())

    def test_workshop_with_registrations_cannot_be_deleted(self):
        w = Workshop.objects.create(code="4", name="Novo")
        Registration.objects.create(**registration_data(workshop="4"))

        self.assertEqual(
            self.client.get(f"/admin/core/workshop/{w.pk}/delete/").status_code, 403
        )
        self.client.post(
            "/admin/core/workshop/",
            {"action": "delete_selected", "_selected_action": [w.pk], "post": "yes"},
        )
        self.assertTrue(Workshop.objects.filter(pk=w.pk).exists())

    def test_changelists_load(self):
        Workshop.objects.create(code="4", name="Novo")
        EventDay.objects.create(date=datetime.date(2026, 10, 21), subtitle="Dia")
        for name in ("workshop", "eventday", "registration"):
            self.assertEqual(
                self.client.get(f"/admin/core/{name}/").status_code, 200, name
            )

    def test_registration_filter_by_workshop(self):
        Workshop.objects.create(code="4", name="Novo")
        Registration.objects.create(
            **registration_data(full_name="Pessoa Xis", email="x@example.com", workshop="4")
        )
        Registration.objects.create(
            **registration_data(full_name="Pessoa Ípsilon", email="y@example.com", workshop="0")
        )

        response = self.client.get("/admin/core/registration/?workshop__exact=4")

        self.assertContains(response, "Pessoa Xis")
        self.assertNotContains(response, "Pessoa Ípsilon")


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


@override_settings(
    STORAGES=PLAIN_STORAGES,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Capivara Tech <evento@example.com>",
    TASKS={"default": {"BACKEND": "django_tasks.backends.database.DatabaseBackend", "QUEUES": ["default", "pictures"]}},
)
class EmailAndCertificatesWithDatabaseWorkshopsTests(TestCase):
    """Fluxos de e-mail e certificados (código de outro dev) com minicursos vindos do banco."""

    def setUp(self):
        Workshop.objects.all().delete()
        Workshop.objects.create(code="1", name="Django Girls", order=1)
        Workshop.objects.create(code="2", name="Teste de Software", order=2, published=False)
        configuration = EmailSettings.get_solo()
        configuration.received_body = "${minicurso}"
        configuration.confirmed_body = "${minicurso}"
        configuration.save()
        self.model_admin = RegistrationAdmin(Registration, AdminSite())

    def test_email_placeholder_shows_the_workshop_for_every_code(self):
        expected = {
            "0": "Não participarei de minicurso",
            "1": "1. Django Girls",
            "2": "2. Teste de Software",  # escondido no site, mas a inscrição continua válida
            "9": "9",  # código sem minicurso cadastrado: não pode derrubar o envio
        }
        for code, label in expected.items():
            with self.subTest(code=code):
                mail.outbox.clear()
                participant = Registration.objects.create(
                    full_name="Ana", email=f"ana{code}@example.com", workshop=code, confirmated=True
                )
                send_registration_email.call(participant.pk, "received")
                send_registration_email.call(participant.pk, "confirmed")
                self.assertEqual([m.body for m in mail.outbox], [label, label])

    def test_registration_through_the_site_sends_the_receipt_with_the_workshop(self):
        response = self.client.post(reverse("registration"), {
            "full_name": "Maria", "email": "maria@example.com",
            "activity": "ORIGIN", "workshop": "1",
        })
        self.assertEqual(response.status_code, 302)
        result = DBTaskResult.objects.get(task_path="core.tasks.send_registration_email")
        send_registration_email.call(*result.args_kwargs["args"])
        self.assertEqual(mail.outbox[0].body, "1. Django Girls")

    def test_confirm_and_resend_actions_work_for_registrations_with_workshops(self):
        participant = Registration.objects.create(full_name="Ana", email="ana@example.com", workshop="2")
        with patch.object(self.model_admin, "message_user"):
            self.model_admin.confirm_registration(None, Registration.objects.all())
            self.model_admin.resend_registration_email(None, Registration.objects.all())
        for row in DBTaskResult.objects.all():
            send_registration_email.call(*row.args_kwargs["args"])
        self.assertEqual({m.body for m in mail.outbox}, {"2. Teste de Software"})
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(Registration.objects.get(pk=participant.pk).confirmated)

    def test_certificate_actions_use_the_workshop_name_from_the_database(self):
        from certification.models import Certificate, CertificationSettings

        CertificationSettings.get_solo()
        Registration.objects.create(full_name="Geral", email="g@example.com", workshop="0", confirmated=True)
        Registration.objects.create(full_name="Mini", email="m@example.com", workshop="2", confirmated=True)
        Registration.objects.create(full_name="Pendente", email="p@example.com", workshop="1")
        with patch.object(self.model_admin, "message_user"):
            self.model_admin.create_certificate(None, Registration.objects.all())
            self.model_admin.create_certificate_workshop(None, Registration.objects.all())

        self.assertEqual(
            sorted(Certificate.objects.values_list("participant_name", "activity", "workload")),
            [
                ("Geral", "V Seminário Piauiense de Agroecologia", 24),
                ("Mini", "Teste de Software", 8),
            ],
        )
