"""Folhas A4 de 30 etiquetas, em pares verticais por participante."""
from decimal import Decimal

from django import forms
from django.template.loader import render_to_string
from weasyprint import HTML

from core.attendance import _sort_key, _static_data_uri
from core.event_config import get_event_config


class LabelPrintForm(forms.Form):
    top = forms.DecimalField(label="Margem superior (mm)", initial="21.5", min_value=0, max_value=43, decimal_places=2)
    left = forms.DecimalField(label="Margem esquerda (mm)", initial="4.95", min_value=0, max_value=9.9, decimal_places=2)
    column_gap = forms.DecimalField(label="Espaço entre colunas (mm)", initial=0, min_value=0, max_value=4.95, decimal_places=2)
    row_gap = forms.DecimalField(label="Espaço entre linhas (mm)", initial=0, min_value=0, max_value=4.77, decimal_places=2)
    guides = forms.BooleanField(label="Mostrar contornos para teste em papel comum", required=False)

    def clean(self):
        data = super().clean()
        if all(k in data for k in ("left", "column_gap")):
            if data["left"] + Decimal("200.1") + 2 * data["column_gap"] > 210:
                self.add_error("column_gap", "As três colunas ultrapassam a largura do A4 (210 mm).")
        if all(k in data for k in ("top", "row_gap")):
            if data["top"] + 254 + 9 * data["row_gap"] > 297:
                self.add_error("row_gap", "As dez linhas ultrapassam a altura do A4 (297 mm).")
        return data


def label_pages(registrations, layout):
    people = sorted((r for r in registrations if r.confirmated), key=lambda r: (_sort_key(r.full_name), r.pk or 0))
    pages = []
    for start in range(0, len(people), 15):
        labels = []
        for index, person in enumerate(people[start:start + 15]):
            row, column = divmod(index, 3)
            x = layout["left"] + column * (Decimal("66.7") + layout["column_gap"])
            for offset, kind in ((0, "event"), (1, "participant")):
                labels.append({
                    "kind": kind, "person": person, "x": x,
                    "y": layout["top"] + (row * 2 + offset) * (Decimal("25.4") + layout["row_gap"]),
                    "font_size": 11 if len(person.full_name) <= 45 else 9 if len(person.full_name) <= 80 else 7 if len(person.full_name) <= 150 else 5.5,
                })
        pages.append(labels)
    return pages


def build_labels_pdf(registrations, layout):
    pages = label_pages(registrations, layout)
    if not pages:
        raise ValueError("Nenhuma inscrição confirmada para imprimir.")
    html = render_to_string("core/labels.html", {
        "pages": pages, "event": get_event_config(), "guides": layout.get("guides", False),
        "logo": _static_data_uri("images/capivara-logo.svg"),
    })
    return HTML(string=html).write_pdf()
