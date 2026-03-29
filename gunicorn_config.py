# Gunicorn configuration for SRESource

import multiprocessing
import logging

# Server socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "sresource"

# Server mechanics
daemon = False
pidfile = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None

# Server hooks
def when_ready(server):
    logging.getLogger("gunicorn.access").info("SRESource server is ready. Spawning workers")

def on_starting(server):
    logging.getLogger("gunicorn.error").info("Gunicorn server starting...")

def on_exit(server):
    logging.getLogger("gunicorn.error").info("Gunicorn server exiting")
