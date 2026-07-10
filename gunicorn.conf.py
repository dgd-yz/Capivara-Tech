import multiprocessing
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
wsgi_app = "seminarioagroecologiav.wsgi:application"
accesslog = "-"
errorlog = "-"
