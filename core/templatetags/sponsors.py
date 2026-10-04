from django import template

from core.models import Sponsor

register = template.Library()


@register.inclusion_tag("core/_sponsors_section.html")
def sponsors_section():
    groups = Sponsor.grouped()
    return {
        "groups": groups,
        "master": next((g for g in groups if g["key"] == "master"), None),
        "tiers": [g for g in groups if g["key"] != "master"],
    }


@register.inclusion_tag("core/_sponsors_footer.html")
def sponsors_footer():
    # o master já aparece em "Organização" no rodapé
    return {"groups": [g for g in Sponsor.grouped() if g["key"] != "master"]}
