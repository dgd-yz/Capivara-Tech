"""Renderização sem requisições HTTP ao próprio servidor nem acesso arbitrário a arquivos."""
import base64
import mimetypes
from urllib.parse import unquote, urljoin, urlsplit
from pathlib import PurePosixPath

from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.staticfiles import finders
from weasyprint import default_url_fetcher


def image_data_uri(field):
    if not field:
        return ""
    with field.open("rb") as stream:
        content = stream.read()
    mime = mimetypes.guess_type(field.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"


def certificate_url_fetcher(base_url):
    def fetch(url):
        parsed = urlsplit(url)
        if parsed.scheme == "data":
            return default_url_fetcher(url)
        for prefix, storage in ((settings.MEDIA_URL, default_storage), (settings.STATIC_URL, staticfiles_storage)):
            root = urlsplit(urljoin(base_url, prefix))
            if parsed.scheme not in {"http", "https"} or parsed.netloc != root.netloc:
                continue
            path, root_path = unquote(parsed.path), unquote(root.path)
            if not path.startswith(root_path):
                continue
            name = path[len(root_path):]
            if not name or ".." in PurePosixPath(name).parts or "\\" in name:
                raise ValueError("Caminho de imagem inválido")
            if storage is staticfiles_storage and not storage.exists(name):
                found = finders.find(name)
                if not found:
                    raise ValueError("Imagem estática não encontrada")
                with open(found, "rb") as stream:
                    content = stream.read()
            else:
                with storage.open(name, "rb") as stream:
                    content = stream.read()
            return {"string": content, "mime_type": mimetypes.guess_type(name)[0] or "application/octet-stream"}
        raise ValueError("Use imagens enviadas pelo editor; recursos externos não são carregados no certificado.")
    return fetch
