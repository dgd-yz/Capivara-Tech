from django.urls import include, path

from .views import (
    about,
    accommodations,
    contact,
    home,
    registration,
    schedule,
    signup,
    submissions,
)

urlpatterns = [
    path("", home, name="home"),
    path("sobre", about, name="about"),
    path("programação", schedule, name="schedule"),
    path("inscrição", registration, name="registration"),
    path("hospedagens", accommodations, name="accommodations"),
    path("submissões", submissions, name="submissions"),
    path("contato", contact, name="contact"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/create/", signup, name="signup"),
]
