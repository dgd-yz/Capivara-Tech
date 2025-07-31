FROM python:3.12-alpine3.19

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT 8000

RUN apk update && \
    apk add git gcc musl-dev libffi-dev pango fontconfig ttf-dejavu cairo
# apk add so:libgobject-2.0.so.0 so:libpango-1.0.so.0 so:libharfbuzz.so.0 so:libharfbuzz-subset.so.0 so:libfontconfig.so.1 so:libpangoft2-1.0.so.0

WORKDIR /app 

COPY requirements.txt .
RUN pip3 install -r requirements.txt --no-cache-dir
COPY . . 

RUN python3 manage.py collectstatic --no-input

EXPOSE ${PORT}  
ENTRYPOINT ["python3"]
CMD ["-m", "gunicorn", "-c", "gunicorn.conf.py"]
