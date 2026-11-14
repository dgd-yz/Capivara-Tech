from itertools import groupby

from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import Resolver404, resolve
from django.utils import timezone

from core.event_config import get_event_config

from .models import CourseSettings, Highlight, Subject, Topic


def home(request):
    subjects = Subject.objects.all()
    modules = [
        {"number": number, "subjects": items, "workload": sum(s.workload or 0 for s in items)}
        for number, group in groupby(subjects, key=lambda s: s.module)
        for items in [list(group)]
    ]
    return render(request, "curso/home.html", {
        "course": CourseSettings.get_solo(),
        "topics": Topic.objects.filter(published=True),
        "modules": modules,
        "highlights": Highlight.objects.filter(published=True)[:6],
        "event_past": get_event_config()["end_date"] < timezone.localdate(),
        "event_url": settings.EVENT_ORIGIN.rstrip("/") + "/" if settings.EVENT_ORIGIN else "",
    })


def event_redirect(request, path=""):
    """Links antigos do Capivara Tech (certificados, QR codes, e-mails) que chegam no domínio do curso.

    Redirecionamento temporário (302): se o curso ganhar uma página com o mesmo endereço, nenhum
    navegador fica preso a um 301 antigo.
    """
    if not settings.EVENT_ORIGIN:
        raise Http404
    try:
        resolve(request.path_info, urlconf=settings.ROOT_URLCONF)
    except Resolver404:
        raise Http404
    return redirect(settings.EVENT_ORIGIN.rstrip("/") + request.get_full_path())
