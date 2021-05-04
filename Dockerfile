FROM python:3.8.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ssh && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /key
# Git ignores this file
COPY private_ssh_key .
# COPY ssh_config /root/.ssh/config

WORKDIR /app
# Re-create the requirements layer if the requirements change
COPY requirements.txt /app/
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

# Re-create the code layer if the file changes
COPY deployhook.py /app/

# Move this later above
COPY ssh_config /root/.ssh/config

# 1 worker, 4 worker threads should be more than enough.
# --worker-class gthread is automatically set if --threads > 1.

# In my experience this configuration hovers around 100 MB
# baseline (noop app code) memory usage in Cloud Run.

# --timeout 0 disables gunicorn's automatic worker restarting.
# "Workers silent for more than this many seconds are killed and restarted."

# If things get bad you might want to --max-requests, --max-requests-jitter, --workers 2.
# TODO: memory usage metrics

# EXPOSE 8080
CMD exec gunicorn --bind :8080 --workers 1 --threads 4 --timeout 0 deployhook:app
