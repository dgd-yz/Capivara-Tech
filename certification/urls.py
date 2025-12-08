from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from .views import certificate_detail

urlpatterns = [
    path("certificado/<uuid:uuid>", certificate_detail, name="certificate_detail"),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
