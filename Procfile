web: -m gunicorn -c gunicorn.conf.py --reload
worker: ./manage.py db_worker --queue-name *
release: ./manage.py migrate