#!/usr/bin/env python3
#
# This script can send POST requests to your development set up or the staging instance
import hashlib
import hmac
import json
import logging
import os
import sys

import requests
import click

from config import SENTRY_REPO, LOGGING_LEVEL
from lib import run

logging.basicConfig(format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)

HOSTS = {
    "dev": "http://0.0.0.0",
    "staging": "https://sentry-deploy-sync-hook-staging-dwunkkvj6a-uc.a.run.app",
}

# For testing against development, we can call this script with or without using secrets
# For production/staging you will need these defined
GH_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")
GITBOT_SECRET = os.environ.get("GITBOT_SECRET")


def signature(secret, payload):
    return hmac.new(
        secret.encode("utf-8"), json.dumps(payload).encode("utf-8"), hashlib.sha1
    ).hexdigest()


def revert_payload_header(repo, sha, author, email):
    payload = {"repo": repo, "sha": sha, "name": f"{author} <{email}>"}
    header = {}
    if GITBOT_SECRET:
        sign = signature(GITBOT_SECRET, payload)
        header["X-Signature"] = f"sha1={sign}"
    return payload, header


@click.command()
@click.option("--host", default="dev", help="Host to test against.")
@click.option("--port", help="The port to use.")  # Optional
@click.option("--action", help="Action to take: [reset|revert].")
@click.option("--repo", help="Repo to act on.")
@click.option("--sha", help="Sha to act on.")
@click.option("--author", help="The name of who's making the request.")  # Optional
@click.option("--email", help="The email of who's making the request.")  # Optional
def main(host, port, action, repo, sha, author, email):
    if action == "reset":
        # This guarantees that this script will hit a fresh remote repo, thus, not failing revert requests
        print(
            f"Run this command from your personal Sentry checkout: git push -f git@github.com:{SENTRY_REPO}"
        )
        sys.exit(0)

    host_url = HOSTS[host]

    if port:
        if host == "dev" and not port:
            host_url += ":5000"
        else:
            host_url += f":{port}"

    if not (author and email):
        author = run("git config --global user.name").stdout.decode("utf-8").strip()
        email = run("git config --global user.email").stdout.decode("utf-8").strip()

    if action == "revert":
        payload, header = revert_payload_header(repo, sha, author, email)
        url = f"{host_url}/api/revert"
    else:
        print("Invalid action.")
        sys.exit("1")

    print("Making request")
    resp = requests.post(url, headers=header, json=payload)
    print(resp.text)


if __name__ == "__main__":
    main()
