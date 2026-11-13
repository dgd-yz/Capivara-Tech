from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django_tasks.backends.database.models import DBTaskResult

from core.check_in_import import AMBIGUOUS, EXACT, MISSING, SIMILAR, match_names, normalize, parse_names
from core.models import Registration, Workshop


class Reg:
    def __init__(self, pk, full_name):
        self.pk, self.full_name = pk, full_name


class MatchingTests(SimpleTestCase):
    def test_normalize_ignores_case_accents_and_punctuation(self):
        self.assertEqual(normalize("  JOSÉ  Francisco De Araújo, "), "jose francisco de araujo")

    def test_parse_names_skips_blank_lines_numbering_tabs_and_repetitions(self):
        text = "1 - Ana Silva\n\n2. Bruno Costa\t Sim\n12) Carla Dias\nana silva\n   \n"
        self.assertEqual(parse_names(text), ["Ana Silva", "Bruno Costa", "Carla Dias"])

    def test_match_statuses(self):
        registrations = [
            Reg(1, "Ana Maria Silva"), Reg(2, "Sabrina Santana Gomes"), Reg(3, "Sabrina Santana Gomes"),
            Reg(4, "Isabela Ribeiro Paes"), Reg(5, "Pedro Henrique Costa Ribeiro Lopes"),
        ]
        rows = match_names(
            ["ANA MARIA SÍLVA", "Sabrina Santana Gomes", "Isabela Ribeiro", "Pedro Henrique Costa Ribeiro Lopez", "Zé Ninguém"],
            registrations,
        )
        self.assertEqual([r.status for r in rows], [EXACT, AMBIGUOUS, SIMILAR, SIMILAR, MISSING])
        self.assertEqual(rows[0].preselected, 1)
        self.assertEqual({r.pk for r, _ in rows[1].candidates}, {2, 3})
        self.assertIsNone(rows[1].preselected)
        self.assertEqual(rows[2].candidates[0][0].pk, 4)
        self.assertIsNone(rows[2].preselected)
        self.assertEqual(rows[3].candidates[0][0].pk, 5)
        self.assertEqual(rows[4].candidates, [])


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CheckInImportViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username="import-admin", email="admin@example.com", password=None,
        )
        cls.workshop = Workshop.objects.create(code="98", name="Curso de importação", capacity=20, workload=4)

    def setUp(self):
        self.client.force_login(self.admin_user)
        self.url = reverse("admin:core_registration_check_in_import")

    def participant(self, name, **kwargs):
        return Registration.objects.create(full_name=name, email=f"{normalize(name).replace(' ', '.')}@example.com", **kwargs)

    def test_changelist_links_to_import(self):
        response = self.client.get(reverse("admin:core_registration_changelist"))
        self.assertContains(response, self.url)

    def test_preview_writes_nothing_and_preselects_only_exact_matches(self):
        exact = self.participant("Ana Maria Silva")
        similar = self.participant("Isabela Ribeiro Paes")
        response = self.client.post(self.url, {"scope": "all", "names": "Ana Maria Silva\nIsabela Ribeiro\nZé Ninguém"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'value="{exact.pk}" checked>')
        self.assertContains(response, f'value="{similar.pk}">')
        self.assertNotContains(response, f'value="{similar.pk}" checked>')
        self.assertContains(response, "Não encontrados")
        self.assertFalse(Registration.objects.filter(checked_in=True).exists())

    def test_apply_checks_in_selected_without_confirming_or_sending_email(self):
        walk_in = self.participant("Ana Maria Silva")  # inscrição feita no dia, nunca confirmada
        other = self.participant("Bruno Costa")
        response = self.client.post(self.url, {
            "step": "apply", "scope": "all", "names": "Ana Maria Silva\nZé Ninguém",
            "registration": [walk_in.pk, other.pk],  # `other` não está na lista: é ignorado
        })
        self.assertEqual(response.status_code, 200)
        walk_in.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(walk_in.checked_in)
        self.assertFalse(walk_in.confirmated)
        self.assertFalse(other.checked_in)
        self.assertContains(response, "Zé Ninguém")
        self.assertFalse(DBTaskResult.objects.exists())

    def test_scope_limits_matching_to_the_chosen_list(self):
        general = self.participant("César Dias Soares", workshop="0")
        workshop = self.participant("César Dias Soares", workshop=self.workshop.code)
        response = self.client.post(self.url, {"scope": "0", "names": "César Dias Soares"})
        self.assertContains(response, f'value="{general.pk}"')
        self.assertNotContains(response, f'value="{workshop.pk}"')
        self.client.post(self.url, {"step": "apply", "scope": "0", "names": "César Dias Soares",
                                    "registration": [general.pk, workshop.pk]})
        general.refresh_from_db()
        workshop.refresh_from_db()
        self.assertTrue(general.checked_in)
        self.assertFalse(workshop.checked_in)

    def test_requires_change_permission(self):
        viewer = get_user_model().objects.create_user("import-viewer", is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename="view_registration", content_type__app_label="core"))
        self.client.force_login(viewer)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertNotContains(self.client.get(reverse("admin:core_registration_changelist")), self.url)
