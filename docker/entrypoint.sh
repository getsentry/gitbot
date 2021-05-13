#!/bin/bash
# This Docker entrypoint guarantees that a private key will be generated
set -e

# Try to create the private key
if [ ! -f /app/private_ssh_key ] && [ -n "${DEPLOY_SSH_KEY}" ]; then
    # Writing an SSH key via UNIX tools was tricky
    /app/write_to_disk.py
    chmod 600 /app/private_ssh_key
fi

# If the private key has not been written we should abort
if [ ! -f /app/private_ssh_key ]; then
    echo -e "The container needs a private key and this is created via DEPLOY_SSH_KEY (see docs for details)" >&2
    exit 1
fi

exec "$@"
