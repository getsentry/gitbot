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

# If the key has a passphrase this will fail
# This verifies that the key is in the right format, however, even on success it exits with non-success
# XXX: Comment out temporarily
# ssh -T git@github.com -v -i /app/private_ssh_key ||
#     [ ${?} == 255 ] && echo "The key is an improper format. Look into it." && rm /app/private_ssh_key && exit 1

exec "$@"
