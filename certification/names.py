"""Padroniza nomes de pessoas para o certificado (as inscrições continuam como foram digitadas)."""
import re

PARTICLES = {"de", "da", "do", "das", "dos", "e"}
ROMAN = re.compile(r"^(i{1,3}|iv|vi{0,3}|ix|x)$", re.IGNORECASE)


def _format_part(part):
    if not part:
        return part
    if ROMAN.match(part):
        return part.upper()
    # "McDonald", "DeLuca": maiúscula no meio da palavra foi escrita de propósito.
    if any(c.isupper() for c in part[1:]) and any(c.islower() for c in part):
        return part
    return part[0].upper() + part[1:].lower()


def _format_word(word, first):
    if not first and word.lower() in PARTICLES:
        return word.lower()
    # Abreviação ("C.", "G.") ou inicial solta.
    if re.fullmatch(r"\w\.?", word):
        return word.upper()
    return "-".join(_format_part(part) for part in word.split("-"))


def format_person_name(name):
    """Ex.: "ADRIANO DA LUZ PEREIRA" -> "Adriano da Luz Pereira"; "lucas negreiros da silva" -> "Lucas Negreiros da Silva"."""
    words = (name or "").split()
    return " ".join(_format_word(word, index == 0) for index, word in enumerate(words))
