import logging
import os
from distutils import util

from google.cloud import secretmanager


def repo_url_with_pat(repo):
    return f"https://{os.environ['GITBOT_USER']}:{PAT}@github.com/{repo}"


COMMITTER_NAME = "Sentry Bot"
COMMITTER_EMAIL = "bot@getsentry.com"
# Used in Github Sentry PRs to sync a getsentry branch
GITBOT_MARKER = "#sync-getsentry"


# App behaviour
DRY_RUN = bool(util.strtobool(os.environ.get("DRY_RUN", "False")))
ENV = os.environ.get("FLASK_ENV") or os.environ["ENV"]
LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", logging.INFO)
IS_DEV = ENV == "development"

# Secrets
PAT = os.environ.get("GITBOT_PAT")
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")
# On GCR we use Google secrets to fetch the PAT
if not PAT:
    # If you're inside of GCR you don't need to set any env variables
    # If you want to test locally you will have to set GOOGLE_APPLICATION_CREDENTIALS to the path of the GCR key
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()
    # GCP project in which to store secrets in Secret Manager.
    PAT = client.access_secret_version(
        name="projects/sentry-dev-tooling/secrets/GitbotPat/versions/1"
    ).payload.data.decode("UTF-8")
    version = 1 if ENV != "production" else 2
    GITHUB_WEBHOOK_SECRET = client.access_secret_version(
        name=f"projects/sentry-dev-tooling/secrets/GitbotGithubSecret/versions/{version}"
    ).payload.data.decode("UTF-8")


# Repo related constants
GETSENTRY_BRANCH = "master"
GETSENTRY_CHECKOUT_PATH = "/tmp/getsentry"
GETSENTRY_REPO = os.environ.get("GETSENTRY_REPO", "getsentry/getsentry-test-repo")
GETSENTRY_REPO_WITH_PAT = repo_url_with_pat(GETSENTRY_REPO)
SENTRY_REPO = os.environ.get("SENTRY_REPO", "sentry/getsentry-test-repo")
