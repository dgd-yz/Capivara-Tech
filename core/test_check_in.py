from unittest.mock import patch

from django.contrib import messages
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django_tasks.backends.database.models import DBTaskResult

from certification.models import Certificate, CertificationSettings
from core.admin import RegistrationAdmin
from core.forms import RegistrationForm
from core.models import Registration, Workshop


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CheckInTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="check-in-admin", email="admin@example.com", password=None,
        )
        cls.workshop = Workshop.objects.create(code="99", name="Curso de credenciamento", capacity=20, workload=4)

    def setUp(self):
        self.client.force_login(self.admin_user)
        self.model_admin = RegistrationAdmin(Registration, AdminSite())
        self.changelist = reverse("admin:core_registration_changelist")

    def participant(self, name="Participante", **kwargs):
        return Registration.objects.create(full_name=name, email=f"{name.lower()}@example.com", **kwargs)

    def test_check_in_defaults_to_false(self):
        self.assertFalse(self.participant().checked_in)

    def test_public_form_cannot_set_check_in_even_with_forged_post(self):
        self.client.logout()
        form = RegistrationForm({
            "full_name": "Visitante", "email": "visitante@example.com",
            "activity": "ORIGIN", "workshop": "0", "checked_in": "on", "confirmated": "on",
        })
        self.assertNotIn("checked_in", form.fields)
        self.assertTrue(form.is_valid(), form.errors)
        participant = form.save()
        self.assertFalse(participant.checked_in)
        self.assertFalse(participant.confirmated)

    def test_admin_edit_exposes_and_saves_check_in_without_confirming_or_queueing(self):
        participant = self.participant()
        url = reverse("admin:core_registration_change", args=[participant.pk])
        self.assertContains(self.client.get(url), 'name="checked_in"')
        response = self.client.post(url, {
            "full_name": participant.full_name, "email": participant.email,
            "activity": "ORIGIN", "workshop": "0", "organization": "NONE",
            "checked_in": "on", "_save": "Salvar",
        })
        self.assertEqual(response.status_code, 302)
        participant.refresh_from_db()
        self.assertTrue(participant.checked_in)
        self.assertFalse(participant.confirmated)
        self.assertFalse(DBTaskResult.objects.exists())

    def test_admin_lists_check_in_and_filters_participants(self):
        self.participant("Presente", checked_in=True)
        self.participant("Ausente")
        response = self.client.get(self.changelist, {"checked_in__exact": "1"})
        self.assertContains(response, "Credenciado?")
        self.assertContains(response, "Presente")
        self.assertNotContains(response, "Ausente")
        response = self.client.get(self.changelist, {"checked_in__exact": "0"})
        self.assertContains(response, "Ausente")
        self.assertNotContains(response, "Presente")

    def test_check_in_can_be_checked_and_unchecked_directly_in_the_list(self):
        self.workshop.capacity = 1
        self.workshop.save()
        participant = self.participant("Selecionado", workshop=self.workshop.code)
        other = self.participant("Outro", confirmated=True)
        response = self.client.get(self.changelist)
        formset = response.context["cl"].formset
        self.assertIsNotNone(formset)
        self.assertContains(response, 'name="_save"')
        data = {f"{formset.prefix}-{key}": value for key, value in formset.management_form.initial.items()}
        data["_save"] = "Salvar"
        for form in formset.forms:
            data[f"{form.prefix}-id"] = form.instance.pk
            if form.instance.pk == participant.pk:
                checkbox = f"{form.prefix}-checked_in"
                self.assertContains(response, f'name="{checkbox}"')
                data[checkbox] = "on"

        self.assertEqual(self.client.post(self.changelist, data).status_code, 302)
        participant.refresh_from_db()
        self.assertTrue(participant.checked_in)
        del data[checkbox]
        self.assertEqual(self.client.post(self.changelist, data).status_code, 302)
        participant.refresh_from_db()
        other.refresh_from_db()
        self.assertFalse(participant.checked_in)
        self.assertFalse(participant.confirmated)
        self.assertFalse(other.checked_in)
        self.assertTrue(other.confirmated)
        self.assertFalse(DBTaskResult.objects.exists())

    def test_view_only_user_cannot_save_check_in_from_the_list(self):
        participant = self.participant()
        viewer = get_user_model().objects.create_user("list-viewer", is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename="view_registration", content_type__app_label="core"))
        self.client.force_login(viewer)
        response = self.client.get(self.changelist)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["cl"].formset)
        response = self.client.post(self.changelist, {
            "_save": "Salvar", "form-TOTAL_FORMS": 1, "form-INITIAL_FORMS": 1,
            "form-0-id": participant.pk, "form-0-checked_in": "on",
        })
        self.assertEqual(response.status_code, 403)
        participant.refresh_from_db()
        self.assertFalse(participant.checked_in)

    def test_bulk_check_in_only_changes_selected_participants_and_sends_no_email(self):
        selected = self.participant("Selecionado")
        other = self.participant("Outro")
        for _ in range(2):
            response = self.client.post(self.changelist, {
                "action": "mark_checked_in", "_selected_action": [selected.pk],
            })
            self.assertEqual(response.status_code, 302)
        selected.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(selected.checked_in)
        self.assertFalse(selected.confirmated)
        self.assertFalse(other.checked_in)
        self.assertFalse(DBTaskResult.objects.exists())

    def test_undo_check_in_preserves_confirmation_and_existing_certificates(self):
        selected = self.participant("Selecionado", checked_in=True, confirmated=True)
        other = self.participant("Outro", checked_in=True)
        self.run_generation("create_certificate", Registration.objects.filter(pk=selected.pk))
        self.assertEqual(Certificate.objects.count(), 1)
        for _ in range(2):
            response = self.client.post(self.changelist, {
                "action": "undo_check_in", "_selected_action": [selected.pk],
            })
            self.assertEqual(response.status_code, 302)
        selected.refresh_from_db()
        other.refresh_from_db()
        self.assertFalse(selected.checked_in)
        self.assertTrue(selected.confirmated)
        self.assertTrue(other.checked_in)
        self.assertEqual(Certificate.objects.count(), 1)
        self.assertFalse(DBTaskResult.objects.exists())

    def test_check_in_and_generation_actions_require_change_permission(self):
        viewer = get_user_model().objects.create_user("viewer", is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename="view_registration", content_type__app_label="core"))
        request = RequestFactory().get(self.changelist)
        request.user = viewer
        actions = self.model_admin.get_actions(request)
        for action in ["mark_checked_in", "undo_check_in", "create_certificate", "create_certificate_workshop"]:
            self.assertNotIn(action, actions)

    def run_generation(self, action, queryset=None):
        if queryset is None:
            queryset = Registration.objects.all()
        with patch.object(self.model_admin, "message_user") as notice:
            getattr(self.model_admin, action)(None, queryset)
        return notice.call_args.args

    def make_eligibility_matrix(self):
        for confirmed in [False, True]:
            for checked_in in [False, True]:
                for workshop in ["0", self.workshop.code]:
                    self.participant(
                        f"P{int(confirmed)}{int(checked_in)}{workshop}",
                        confirmated=confirmed, checked_in=checked_in, workshop=workshop,
                    )

    def test_general_certificate_requires_confirmation_and_check_in(self):
        self.make_eligibility_matrix()
        _, message, level = self.run_generation("create_certificate")
        self.assertCountEqual(
            Certificate.objects.values_list("participant_name", flat=True), ["P110", "P1199"],
        )
        self.assertIn("2 participantes elegíveis processados", message)
        self.assertIn("6 inscrições ignoradas por falta de confirmação ou credenciamento", message)
        self.assertEqual(level, messages.WARNING)

    def test_workshop_certificate_also_requires_a_workshop(self):
        self.make_eligibility_matrix()
        _, message, _ = self.run_generation("create_certificate_workshop")
        certificate = Certificate.objects.get()
        self.assertEqual(certificate.participant_name, "P1199")
        self.assertEqual(certificate.activity, self.workshop.name)
        self.assertEqual(certificate.workload, self.workshop.workload)
        self.assertIn("6 inscrições ignoradas por falta de confirmação ou credenciamento", message)
        self.assertIn("1 inscrição ignorada por não ter minicurso", message)

    def test_all_ineligible_produces_warning_without_certificates(self):
        self.participant(confirmated=True)
        _, message, level = self.run_generation("create_certificate")
        self.assertIn("0 participantes elegíveis processados", message)
        self.assertEqual(level, messages.WARNING)
        self.assertFalse(Certificate.objects.exists())

    def test_repeated_generation_reuses_existing_certificates(self):
        self.participant(confirmated=True, checked_in=True, workshop=self.workshop.code)
        for _ in range(2):
            self.run_generation("create_certificate")
            self.run_generation("create_certificate_workshop")
        self.assertEqual(Certificate.objects.count(), 2)

    def test_manual_certificate_creation_remains_available_without_registration(self):
        configuration = CertificationSettings.get_solo()
        url = reverse("admin:certification_certificate_add")
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, {
            "participant_name": "Convidado especial", "participant_email": "convidado@example.com",
            "activity": "Participação especial", "workload": 2,
            "location": configuration.default_location, "date": "2026-10-21",
            "certifier_name": configuration.default_certifier_name,
            "certifier_position": configuration.default_certifier_position,
            "text": configuration.default_text, "_save": "Salvar",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Certificate.objects.get().participant_name, "Convidado especial")
        self.assertFalse(Registration.objects.exists())
