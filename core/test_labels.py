from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from weasyprint import HTML

from core.labels import LabelPrintForm, build_labels_pdf, label_pages
from core.models import Registration


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class LabelTests(TestCase):
    def setUp(self):
        self.data = {"top": "11.5", "left": "4.5", "column_gap": "3.4", "row_gap": "0"}
        form = LabelPrintForm(self.data)
        self.assertTrue(form.is_valid())
        self.layout = form.cleaned_data
        self.url = reverse("admin:core_registration_labels")

    def test_pairs_pagination_sort_and_only_confirmed(self):
        for index in range(16):
            Registration.objects.create(full_name=f"Pessoa {index:02}", confirmated=True)
        Registration.objects.create(full_name="Não imprimir", confirmated=False)
        pages = label_pages(Registration.objects.order_by("-full_name"), self.layout)
        self.assertEqual([len(page) for page in pages], [30, 2])
        self.assertEqual(pages[0][0]["person"].full_name, "Pessoa 00")
        for page in pages:
            for event, person in zip(page[::2], page[1::2]):
                self.assertEqual((event["kind"], person["kind"]), ("event", "participant"))
                self.assertEqual(event["person"], person["person"])
                self.assertEqual(event["x"], person["x"])
                self.assertEqual(float(person["y"] - event["y"]), 25.4)
                self.assertLessEqual(float(person["x"]) + 66.7, 215.9)
                self.assertLessEqual(float(person["y"]) + 25.4, 279.4)
        self.assertEqual([float(label["x"]) for label in pages[0][:6:2]], [4.5, 74.6, 144.7])
        self.assertAlmostEqual(215.9 - float(pages[0][4]["x"]) - 66.7, 4.5)
        self.assertEqual(pages[1][0]["y"], self.layout["top"])

    def test_invalid_layout_cannot_overflow_sheet(self):
        for changes in ({"left": "9.9", "column_gap": "3.4"}, {"top": "40", "row_gap": "1"}, {"left": "-1"}):
            self.assertFalse(LabelPrintForm({**self.data, **changes}).is_valid())

    def test_vertical_correction_keeps_columns_and_label_spacing(self):
        people = [Registration(pk=i + 1, full_name=f"Pessoa {i:02}", confirmated=True) for i in range(16)]
        form = LabelPrintForm({**self.data, "vertical_offset": "-8"})
        self.assertTrue(form.is_valid())
        original = label_pages(people, self.layout)
        corrected = label_pages(people, form.cleaned_data)
        for before_page, after_page in zip(original, corrected):
            for before, after in zip(before_page, after_page):
                self.assertEqual(before["x"], after["x"])
                self.assertEqual(before["y"] - after["y"], 8)
        self.assertEqual(float(corrected[0][0]["y"]), 3.5)
        self.assertFalse(LabelPrintForm({**self.data, "vertical_offset": "-12"}).is_valid())
        self.assertFalse(LabelPrintForm({**self.data, "vertical_offset": "32"}).is_valid())

    def test_admin_permissions(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        staff = get_user_model().objects.create_user("staff-labels", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)

    def test_admin_respects_search_and_confirmation(self):
        admin = get_user_model().objects.create_superuser("labels-admin", password="test")
        self.client.force_login(admin)
        selected = Registration.objects.create(full_name="Ana Confirmada", confirmated=True)
        Registration.objects.create(full_name="Ana Pendente", confirmated=False)
        Registration.objects.create(full_name="Bia Confirmada", confirmated=True)
        with patch("core.admin.build_labels_pdf", return_value=b"%PDF-test") as build:
            response = self.client.post(self.url + "?q=Ana", self.data)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(list(build.call_args.args[0]), [selected])
        self.assertContains(self.client.get(self.url), "2 participante(s)")
        response = self.client.post(self.url + "?q=Ausente", self.data)
        self.assertContains(response, "Nenhuma inscrição confirmada")
        self.assertEqual(self.client.get(self.url + "?inexistente=1").status_code, 400)

    def test_real_pdf_and_empty_selection(self):
        person = Registration.objects.create(full_name="Álvaro & Maria", entity="IFPI", confirmated=True)
        self.assertTrue(build_labels_pdf([person], self.layout).startswith(b"%PDF-"))
        with self.assertRaisesMessage(ValueError, "Nenhuma inscrição confirmada"):
            build_labels_pdf([], self.layout)

    def test_rendered_pages_keep_event_text_inside_each_sheet(self):
        documents = []

        def capture_document(*args, **kwargs):
            document = HTML(*args, **kwargs).render()
            documents.append(document)
            return document

        people = [Registration(pk=i + 1, full_name=f"Pessoa {i:02}", confirmated=True) for i in range(16)]
        with patch("core.labels.HTML", side_effect=capture_document):
            build_labels_pdf(people, self.layout)
        pages = documents[0].pages
        self.assertEqual(len(pages), 2)
        for page, expected in zip(pages, (15, 1)):
            self.assertAlmostEqual(page.width * 25.4 / 96, 215.9)
            self.assertAlmostEqual(page.height * 25.4 / 96, 279.4)
            texts = [box for box in page._page_box.descendants(placeholders=True) if hasattr(box, "text")]
            self.assertEqual(sum(box.text == "PARTICIPANTE" for box in texts), expected)
            event_texts = [box for box in texts if "Capivara" in box.text]
            self.assertEqual(len(event_texts), expected)
            for box in texts:
                self.assertGreaterEqual(box.position_y, 0)
                self.assertLessEqual(box.position_y + box.height, page.height)
