from datetime import UTC, date, datetime
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import EventDay


@override_settings(STATIC_ROOT=None, STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class ScheduleCurrentDayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        EventDay.objects.all().delete()
        for number in range(1, 4):
            EventDay.objects.create(date=date(2026, 10, 20 + number), subtitle=f"Programação do dia {number}")

    def get_at(self, moment, route="schedule", **headers):
        with patch("core.views.timezone.now", return_value=moment):
            return self.client.get(reverse(route), **headers)

    def assert_selected_day(self, response, day_number):
        self.assertEqual(response.status_code, 200)
        active = [day for day in response.context["schedule_days"] if day.is_active]
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].date, date(2026, 10, 20 + day_number))
        position = next(i for i, day in enumerate(response.context["schedule_days"], 1) if day.is_active)
        self.assertContains(response, f'<div class="ct-day is-active" data-day="{position}">', count=1)
        self.assertContains(response, 'aria-pressed="true"', count=1)

    def test_second_day_is_selected_on_home_and_schedule_with_past_and_today_badges(self):
        for route in ["home", "schedule"]:
            with self.subTest(route=route):
                response = self.get_at(datetime(2026, 10, 22, 15, tzinfo=UTC), route)
                self.assert_selected_day(response, 2)
                self.assertContains(response, '<span class="ct-tab__status">Já passou</span>', count=1)
                self.assertContains(response, '<span class="ct-tab__status">Hoje</span>', count=1)
                self.assertContains(response, 'class="ct-tab is-past" data-day="1" aria-pressed="false"')
                self.assertContains(response, 'class="ct-tab is-active is-today" data-day="2" aria-pressed="true"')
                self.assertNotContains(response, 'class="ct-day is-active" data-day="1"')

    def test_third_day_is_selected_automatically(self):
        response = self.get_at(datetime(2026, 10, 23, 15, tzinfo=UTC))
        self.assert_selected_day(response, 3)
        self.assertContains(response, '<span class="ct-tab__status">Já passou</span>', count=2)
        self.assertContains(response, '<span class="ct-tab__status">Hoje</span>', count=1)

    def test_before_event_selects_first_day_without_past_or_today_badges(self):
        response = self.get_at(datetime(2026, 10, 20, 15, tzinfo=UTC))
        self.assert_selected_day(response, 1)
        self.assertNotContains(response, 'class="ct-tab__status"')

    def test_after_event_selects_last_day_and_marks_all_as_past(self):
        response = self.get_at(datetime(2026, 10, 24, 15, tzinfo=UTC))
        self.assert_selected_day(response, 3)
        self.assertContains(response, '<span class="ct-tab__status">Já passou</span>', count=3)
        self.assertNotContains(response, '<span class="ct-tab__status">Hoje</span>')

    def test_hidden_current_day_selects_next_published_day(self):
        EventDay.objects.filter(date=date(2026, 10, 22)).update(published=False)
        response = self.get_at(datetime(2026, 10, 22, 15, tzinfo=UTC))
        self.assert_selected_day(response, 3)
        self.assertNotContains(response, "22/10")
        self.assertNotContains(response, "Programação do dia 2")

    @override_settings(TIME_ZONE="UTC")
    def test_day_changes_at_midnight_in_brasilia_even_when_server_uses_utc(self):
        for moment, expected in [
            (datetime(2026, 10, 22, 2, 59, tzinfo=UTC), 1),
            (datetime(2026, 10, 22, 3, 0, tzinfo=UTC), 2),
        ]:
            with self.subTest(moment=moment):
                self.assert_selected_day(self.get_at(moment), expected)

    def test_htmx_schedule_keeps_current_day_selection(self):
        response = self.get_at(datetime(2026, 10, 22, 15, tzinfo=UTC), HTTP_HX_REQUEST="true")
        self.assert_selected_day(response, 2)
        self.assertContains(response, '<span class="ct-tab__status">Hoje</span>')
