from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse
from extra_settings.models import Setting

from core.event_config import get_event_config
from core.models import EventDay, ScheduleItem, Workshop


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class EventConfigTests(TestCase):
    def set_value(self, name, value):
        item = Setting.objects.get(name=name)
        item.value = value
        item.save()

    def test_admin_values_appear_on_public_pages_without_restart(self):
        self.set_value("EVENT_NAME", "Encontro de Tecnologia")
        self.set_value("EVENT_START_DATE", date(2027, 5, 10))
        self.set_value("EVENT_END_DATE", date(2027, 5, 12))
        for route in ["home", "about", "registration", "schedule", "certificates"]:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertContains(response, "Encontro de Tecnologia")
                self.assertContains(response, "10 a 12 de maio de 2027")
                self.assertNotContains(response, "outubro de 2026")
        self.set_value("EVENT_NAME", "Novo nome")
        self.assertContains(self.client.get(reverse("home")), "Novo nome")

    def test_dates_across_month_and_year_and_single_day(self):
        self.set_value("EVENT_START_DATE", date(2027, 12, 31))
        self.set_value("EVENT_END_DATE", date(2028, 1, 1))
        config = get_event_config()
        self.assertEqual(config["duration_days"], 2)
        self.assertIn("2027", config["date_label"])
        self.assertIn("2028", config["date_label"])
        self.set_value("EVENT_START_DATE", date(2028, 1, 1))
        self.assertEqual(get_event_config()["date_label"], "1 de janeiro de 2028")

    def test_home_counts_only_published_content(self):
        ScheduleItem.objects.all().delete()
        Workshop.objects.all().delete()
        day = EventDay.objects.create(date=date(2030, 1, 1))
        ScheduleItem.objects.create(day=day, start_time="10:00", title="Talk", tag="palestra")
        ScheduleItem.objects.create(day=day, start_time="11:00", title="Oculta", tag="keynote", published=False)
        Workshop.objects.create(code="7", name="Curso", published=True)
        Workshop.objects.create(code="8", name="Oculto", published=False)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["talks_count"], 1)
        self.assertEqual(len(response.context["workshops"]), 1)
