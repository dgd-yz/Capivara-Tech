import datetime
import shutil
import tempfile
from importlib import import_module
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from core.attendance import workshop_activity
from core.forms import RegistrationAdminForm, RegistrationForm
from core.models import (
    EventDay,
    Registration,
    ScheduleItem,
    Speaker,
    Workshop,
    get_workshops_choices,
)

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
            "core.migrations.0011_import_existing_workshops_and_schedule"
        )
        self.assertEqual(
            [(w["code"], w["name"]) for w in seed.WORKSHOPS],
            [
                ("1", "Django Girls"),
                ("2", "Teste de Software"),
                ("3", "Desenvolvimento de Games"),
            ],
        )

    def test_get_workshop_name(self):
        Workshop.objects.create(code="1", name="Django Girls")
        self.assertEqual(Registration(workshop="1").get_workshop_name(), "Django Girls")
        with self.assertRaises(Workshop.DoesNotExist):
            Registration(workshop="9").get_workshop_name()


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

    def test_code_is_read_only_and_delete_is_blocked(self):
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

        self.assertEqual(
            self.client.get(f"/admin/core/workshop/{w.pk}/delete/").status_code, 403
        )

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
