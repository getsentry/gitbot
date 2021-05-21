FROM python:3.8.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ssh && \
    rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
# Re-create the requirements layer if the requirements change
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Source code
COPY deployhook.py /app/

# 1 worker, 4 worker threads should be more than enough.
# --worker-class gthread is automatically set if --threads > 1.

# In my experience this configuration hovers around 100 MB
# baseline (noop app code) memory usage in Cloud Run.

# --timeout 0 disables gunicorn's automatic worker restarting.
# "Workers silent for more than this many seconds are killed and restarted."

# If things get bad you might want to --max-requests, --max-requests-jitter, --workers 2.
# XXX: Sadly I need to use this until I figure out how to get rid of the entrypoint
COPY docker/entrypoint.sh /app/docker/
ENTRYPOINT exec /app/docker/entrypoint.sh $0 $@
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "4", "--timeout", "0", "deployhook:app"]