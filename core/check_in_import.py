"""Compara uma lista de nomes (das folhas de frequência) com as inscrições do sistema."""
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from django import forms

PARTICLES = {"de", "da", "do", "das", "dos", "e"}
SIMILARITY_MIN = 0.82
MAX_SUGGESTIONS = 3

EXACT = "exact"
AMBIGUOUS = "ambiguous"
SIMILAR = "similar"
MISSING = "missing"


def normalize(name):
    """Minúsculas, sem acentos, sem pontuação e com espaços simples."""
    text = unicodedata.normalize("NFKD", name.lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z\s]", " ", text)
    return " ".join(text.split())


def tokens(normalized):
    return [word for word in normalized.split() if word not in PARTICLES]


def parse_names(text):
    """Um nome por linha. Ignora linhas vazias, numeração ("12 - Nome", "12. Nome") e repetições."""
    names, seen = [], set()
    for line in (text or "").splitlines():
        line = line.split("\t")[0]
        line = re.sub(r"^\s*\d+\s*[-.)–:]?\s*", "", line).strip()
        if not normalize(line):
            continue
        key = normalize(line)
        if key in seen:
            continue
        seen.add(key)
        names.append(line)
    return names


def similarity(a, b):
    """0 a 1. Considera parecido também quando um nome contém todos os nomes do outro."""
    ratio = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(tokens(a)), set(tokens(b))
    if len(ta) >= 2 and len(tb) >= 2 and (ta <= tb or tb <= ta):
        ratio = max(ratio, 0.9)
    return ratio


@dataclass
class MatchRow:
    name: str
    status: str
    candidates: list = field(default_factory=list)  # [(registration, score)]

    @property
    def preselected(self):
        """Só o encontro exato e único vem marcado; o resto pede uma decisão."""
        return self.candidates[0][0].pk if self.status == EXACT else None


def match_names(names, registrations):
    registrations = list(registrations)
    indexed = [(normalize(r.full_name), r) for r in registrations]
    rows = []
    for name in names:
        key = normalize(name)
        exact = [r for norm, r in indexed if norm == key]
        if len(exact) == 1:
            rows.append(MatchRow(name, EXACT, [(exact[0], 1.0)]))
            continue
        if exact:
            rows.append(MatchRow(name, AMBIGUOUS, [(r, 1.0) for r in exact]))
            continue
        scored = sorted(
            ((r, similarity(key, norm)) for norm, r in indexed),
            key=lambda item: item[1], reverse=True,
        )
        close = [(r, round(score, 2)) for r, score in scored if score >= SIMILARITY_MIN][:MAX_SUGGESTIONS]
        rows.append(MatchRow(name, SIMILAR, close) if close else MatchRow(name, MISSING))
    return rows


ALL_REGISTRATIONS = "all"


class CheckInImportForm(forms.Form):
    scope = forms.ChoiceField(
        label="Comparar com",
        help_text="Use a lista da folha que você está importando, para quem tem duas inscrições "
        "(ex.: evento geral e minicurso) ser credenciado só na certa.",
    )
    names = forms.CharField(
        label="Nomes de quem assinou",
        widget=forms.Textarea(attrs={"rows": 18, "cols": 70, "placeholder": "Um nome por linha"}),
        help_text="Um nome por linha. Pode colar de uma planilha; numeração no início da linha é ignorada.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import get_all_workshops_choices

        choices = [(ALL_REGISTRATIONS, "Todas as inscrições")]
        for code, label in get_all_workshops_choices():
            choices.append((code, "Sem minicurso (evento geral)" if code == "0" else f"Minicurso {label}"))
        self.fields["scope"].choices = choices

    def clean_names(self):
        names = parse_names(self.cleaned_data["names"])
        if not names:
            raise forms.ValidationError("Informe pelo menos um nome.")
        return names

    def registrations(self):
        from core.models import Registration

        queryset = Registration.objects.order_by("full_name")
        scope = self.cleaned_data["scope"]
        return queryset if scope == ALL_REGISTRATIONS else queryset.filter(workshop=scope)
