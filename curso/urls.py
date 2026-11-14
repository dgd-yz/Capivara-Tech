"""Rotas do domínio do curso (COURSE_HOSTS). O resto continua no Capivara Tech."""
from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve as media_serve

from core.views import health

from . import views

urlpatterns = [
    path("", views.home, name="curso_home"),
    path("health/", health),
    re_path(r"^uploads/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]

urlpatterns += [
    # Qualquer outro endereço que exista no Capivara Tech vai para o subdomínio do evento.
    re_path(r"^(?P<path>.*)$", views.event_redirect),
]
