#!/usr/bin/env python3
# This script is temporary until we can switch to using Google Secret Manager
import os

# Import the Secret Manager client library.
from google.cloud import secretmanager

FILE = "private_ssh_key"

if os.environ.get("DEPLOY_SSH_KEY"):
    KEY = os.environ["DEPLOY_SSH_KEY"]
    # When the key is a single line, it will contain \n characters representing new lines
    # that need to be removed when writing to disk
    # This is to support local development versus GCR execution
    if KEY.find("\n") != -1:
        contents = KEY.split("\n")
        with open(FILE, "w") as f:
            f.writelines("%s\n" % line for line in contents)
    elif KEY.find("\\n") != -1:
        contents = KEY.split("\\n")
        with open(FILE, "w") as f:
            f.writelines("%s\n" % line for line in contents)
    else:
        with open(FILE, "w") as f:
            f.write(KEY + "\n")
else:
    # If you're inside of GCR you don't need to set any env variables
    # If you want to test locally you will have to set GOOGLE_APPLICATION_CREDENTIALS to the path of the GCR key
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()
    # GCP project in which to store secrets in Secret Manager.
    response = client.access_secret_version(
        name="projects/sentry-dev-tooling/secrets/DeploySyncSshKey/versions/1"
    )
    KEY = response.payload.data.decode("UTF-8")
    with open(FILE, "w") as f:
        f.write(KEY + "\n")
