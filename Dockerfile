FROM python:3.8-slim

COPY requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

# 1 worker, 4 worker threads should be more than enough.
# --worker-class gthread is automatically set if --threads > 1.

# In my experience this configuration hovers around 100 MB
# baseline (noop app code) memory usage in Cloud Run.

# --timeout 0 disables gunicorn's automatic worker restarting.
# "Workers silent for more than this many seconds are killed and restarted."

# If things get bad you might want to --max-requests, --max-requests-jitter, --workers 2.
# TODO: memory usage metrics

CMD exec gunicorn --bind :8080 --workers 1 --threads 4 --timeout 0 deployhook:app
