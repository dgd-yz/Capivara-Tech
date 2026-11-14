web: python3 -m gunicorn -c gunicorn.conf.py
worker: python3 manage.py db_worker --queue-name default,pictures
release: python3 manage.py migrate --noinput
