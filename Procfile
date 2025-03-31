web: -m gunicorn -c gunicorn.conf.py --reload
worker: ./manage.py db_worker
release: ./manage.py migrate