from django.conf import settings
from django.http.request import split_domain_port


class CourseHostMiddleware:
    """Mostra a página do curso nos domínios de COURSE_HOSTS; os demais seguem com o Capivara Tech."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        hosts = {host.lower() for host in settings.COURSE_HOSTS}
        if hosts:
            domain, _port = split_domain_port(request.get_host())
            if domain in hosts:
                request.urlconf = "curso.urls"
        return self.get_response(request)
