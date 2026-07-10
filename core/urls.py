from django.urls import include, path

from .views import (
    about,
    accommodations,
    certificates,
    contact,
    gallery,
    health,
    home,
    letter,
    registration,
    schedule,
    signup,
    submissions,
)

urlpatterns = [
    path("", home, name="home"),
    path("health/", health, name="health"),
    path("sobre", about, name="about"),
    path("programação", schedule, name="schedule"),
    path("inscrição", registration, name="registration"),
    path("hospedagens", accommodations, name="accommodations"),
    path("submissões", submissions, name="submissions"),
    path("contato", contact, name="contact"),
    path("certificados", certificates, name="certificates"),
    path("carta", letter, name="letter"),
    path("galeria", gallery, name="gallery"),
    path("", include("certification.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/create/", signup, name="signup"),
]
