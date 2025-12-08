from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse

from certification.models import Certificate
from core.tasks import send_email

from .forms import CertificatesForm, ContactForm, RegistrationForm, UserCreationForm


def with_template(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        context = view_func(request, *args, **kwargs)
        if isinstance(context, dict):
            context["base_template"] = "main.html" if request.htmx else "base.html"
            return render(request, context.pop("template"), context)
        return context

    return wrapper


@with_template
def home(request):
    return {"template": "core/home.html"}


@with_template
def about(request):
    return {"template": "core/about.html"}


@with_template
def schedule(request):
    return {"template": "core/schedule.html"}


@with_template
def registration(request):
    form = RegistrationForm()
    context = {"template": "core/registration.html", "form": form}
    if request.POST:
        form = RegistrationForm(request.POST)
        context["form"] = form
        if form.is_valid():
            # send_email.enqueue(subject, message, sender_name, sender_email)
            form.save()
            messages.add_message(
                request,
                messages.SUCCESS,
                "Inscrição Relizada com sucesso. Obrigado pela sua participação.",
            )

            return redirect(reverse("registration"))
        return context
    return context


@with_template
def accommodations(request):
    return {"template": "core/accommodations.html"}


@with_template
def submissions(request):
    return {"template": "core/submissions.html"}


@with_template
def contact(request):
    form = ContactForm()
    context = {"form": form}

    if request.POST:
        form = ContactForm(request.POST)
        context["form"] = form
        if form.is_valid():
            sender_name = form.cleaned_data["sender_name"]
            sender_email = form.cleaned_data["sender_email"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            send_email.enqueue(subject, message, sender_name, sender_email)
            messages.add_message(
                request, messages.SUCCESS, "Obrigado pela sua mensagem."
            )

            return redirect(reverse("contact"))
        else:
            context["template"] = "core/contact.html"
            return context
    else:
        context["template"] = "core/contact.html"
        return context


@with_template
def certificates(request):
    if request.POST:
        cf = CertificatesForm(request.POST)
        if cf.is_valid():
            email = cf.cleaned_data["email"]
            certificates = Certificate.objects.filter(participant_email=email)
            return {
                "template": "core/certificates.html",
                "cf": cf,
                "certificates": certificates,
            }
    cf = CertificatesForm()
    return {"template": "core/certificates.html", "cf": cf}


def signup(request):
    if request.htmx:
        base_template = "main.html"
    else:
        base_template = "base.html"
    if request.user.is_authenticated:
        return redirect(reverse("home"))
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user is not None:
                login(request, user)
                return redirect(reverse("home"))
            else:
                return redirect(reverse("login"))
        else:
            form = UserCreationForm(request.POST)
            context = {"base_template": base_template, "form": form}
        return render(request, "core/signup.html", context)
    else:
        form = UserCreationForm()
        context = {"base_template": base_template, "form": form}
        return render(request, "core/signup.html", context)
