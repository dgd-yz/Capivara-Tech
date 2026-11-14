from django.test import TestCase, override_settings

from curso.models import CourseSettings, Highlight, Subject, Topic

COURSE = "sistemasparainternet.com"
EVENT = "https://capivaratech.sistemasparainternet.com"

PLAIN_STATIC = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(
    STORAGES=PLAIN_STATIC,
    ALLOWED_HOSTS=[COURSE, "www." + COURSE, "capivaratech." + COURSE, "testserver"],
    COURSE_HOSTS=[COURSE, "www." + COURSE],
    EVENT_ORIGIN=EVENT,
)
class CourseSiteTests(TestCase):
    def test_course_domain_shows_course_page(self):
        response = self.client.get("/", HTTP_HOST=COURSE)
        self.assertTemplateUsed(response, "curso/home.html")
        self.assertContains(response, "Sistemas para Internet")
        self.assertContains(response, "Sua graduação começa aqui")

    def test_www_is_course_too(self):
        response = self.client.get("/", HTTP_HOST="www." + COURSE)
        self.assertTemplateUsed(response, "curso/home.html")

    @override_settings(ALLOWED_HOSTS=[COURSE], COURSE_HOSTS=[COURSE])
    def test_host_with_port(self):
        response = self.client.get("/", HTTP_HOST=COURSE + ":8000")
        self.assertTemplateUsed(response, "curso/home.html")

    def test_event_subdomain_keeps_capivara_tech(self):
        response = self.client.get("/", HTTP_HOST="capivaratech." + COURSE)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertTemplateNotUsed(response, "curso/home.html")

    @override_settings(COURSE_HOSTS=[])
    def test_without_course_hosts_everything_is_capivara_tech(self):
        response = self.client.get("/", HTTP_HOST=COURSE)
        self.assertTemplateUsed(response, "core/home.html")

    def test_old_event_links_redirect_to_event_subdomain(self):
        response = self.client.get("/certificados?x=1", HTTP_HOST=COURSE)
        self.assertRedirects(response, EVENT + "/certificados?x=1", fetch_redirect_response=False)
        self.assertEqual(response.status_code, 302)

        certificate = "/certificado/0b0b0b0b-0000-4000-8000-000000000000"
        response = self.client.get(certificate, HTTP_HOST=COURSE)
        self.assertRedirects(response, EVENT + certificate, fetch_redirect_response=False)

    def test_unknown_path_is_404_on_course_domain(self):
        response = self.client.get("/nao-existe-em-lugar-nenhum", HTTP_HOST=COURSE)
        self.assertEqual(response.status_code, 404)

    @override_settings(EVENT_ORIGIN="")
    def test_no_redirect_without_event_origin(self):
        response = self.client.get("/certificados", HTTP_HOST=COURSE)
        self.assertEqual(response.status_code, 404)

    def test_health_works_on_course_domain(self):
        response = self.client.get("/health/", HTTP_HOST=COURSE)
        self.assertEqual(response.content, b"ok")

    def test_seeded_ppc_content(self):
        self.assertEqual(Subject.objects.count(), 34)
        for module in range(1, 6):
            hours = sum(s.workload for s in Subject.objects.filter(module=module))
            self.assertEqual(hours, 400, f"módulo {module}")
        self.assertTrue(Topic.objects.exists())

    def test_page_lists_matrix_coordination_and_event(self):
        response = self.client.get("/", HTTP_HOST=COURSE)
        self.assertContains(response, "5 módulos, um por semestre")
        self.assertContains(response, "Algoritmos e Lógica de Programação")
        self.assertContains(response, "<span>Coordenação</span>Paul Symon Ribeiro Rocha")
        self.assertNotContains(response, "Professores")
        self.assertContains(response, 'href="%s/"' % EVENT)

    def test_empty_sections_and_items_are_hidden(self):
        Subject.objects.all().delete()
        settings = CourseSettings.get_solo()
        settings.shift = ""
        settings.coordinator = ""
        settings.save()
        response = self.client.get("/", HTTP_HOST=COURSE)
        self.assertNotContains(response, 'id="matriz"')
        self.assertNotContains(response, "Coordenação")
        self.assertNotContains(response, 'id="destaques"')
        self.assertNotContains(response, "<dt>Turno</dt>")

    def test_highlights_show_only_published(self):
        Highlight.objects.create(title="Turma 2026.1 chegou", date="2026-03-02")
        Highlight.objects.create(title="Rascunho escondido", date="2026-03-03", published=False)
        response = self.client.get("/", HTTP_HOST=COURSE)
        self.assertContains(response, "Turma 2026.1 chegou")
        self.assertNotContains(response, "Rascunho escondido")
