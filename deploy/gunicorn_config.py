import multiprocessing

# Gunicorn configuration file
bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4
timeout = 120
keepalive = 5
loglevel = "info"
errorlog = "/home/ini/Desktop/edukomLMS-A/learning/logs/gunicorn_error.log"
accesslog = "/home/ini/Desktop/edukomLMS-A/learning/logs/gunicorn_access.log"
capture_output = True
pidfile = "/home/ini/Desktop/edukomLMS-A/learning/tmp/gunicorn.pid"
daemon = False
