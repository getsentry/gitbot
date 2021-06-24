import logging
import os
from distutils import util

LOGGING_LEVEL = os.environ.get("LOGGING_LEVEL", logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)


def fetch_secret(client: str, uri: str) -> str:
    logger.info(f"Grabbing secret from {uri}")
    return client.access_secret_version(name=uri).payload.data.decode("UTF-8")


def repo_url_with_pat(repo):
    return f"https://{os.environ.get('GITBOT_USER', 'getsentry-bot')}:{PAT}@github.com/{repo}"


COMMITTER_NAME = "Sentry Bot"
COMMITTER_EMAIL = "bot@getsentry.com"
# For now, we're making this to be used in specific steps, however, we will make it global in the future
COMMITER_ENV = {
    "GIT_AUTHOR_NAME": "getsentry-bot",
    "EMAIL": "bot@sentry.io",
}
# Used in Github Sentry PRs to sync a getsentry branch
GITBOT_MARKER = "#sync-getsentry"

# App behaviour
DRY_RUN = bool(util.strtobool(os.environ.get("DRY_RUN", "False")))
ENV = os.environ.get("ENV", "development")
IS_DEV = ENV == "development"

# Secrets
PAT = os.environ.get("GITBOT_PAT")
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")
GITBOT_API_SECRET = os.environ.get("GITBOT_API_SECRET")
# On GCR we use Google secrets to fetch the PAT
if not PAT and not os.environ.get("FAST_STARTUP"):
    # Loading the module here is useful in systems that the package cannot install (e.g. Apple M1)
    from google.cloud import secretmanager

    # If you're inside of GCR you don't need to set any env variables
    # If you want to test locally you will have to set GOOGLE_APPLICATION_CREDENTIALS to the path of the GCR key
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()
    # GCP project in which to store secrets in Secret Manager.
    PAT = fetch_secret(
        client, "projects/sentry-dev-tooling/secrets/GitbotPat/versions/1"
    )
    version = 1 if ENV != "production" else 2
    GITHUB_WEBHOOK_SECRET = fetch_secret(
        client,
        f"projects/sentry-dev-tooling/secrets/GitbotGithubSecret/versions/{version}",
    )
    GITBOT_API_SECRET = fetch_secret(
        client, "projects/sentry-dev-tooling/secrets/GitbotSecret/versions/1"
    )


# Repo related constants
GETSENTRY_BRANCH = "master"
GETSENTRY_CHECKOUT_PATH = "/tmp/getsentry"
GETSENTRY_REPO = os.environ.get("GETSENTRY_REPO", "getsentry/getsentry-test-repo")
GETSENTRY_REPO_WITH_PAT = repo_url_with_pat(GETSENTRY_REPO)
SENTRY_CHECKOUT_PATH = "/tmp/sentry"
SENTRY_REPO = os.environ.get("SENTRY_REPO", "getsentry/sentry-test-repo")
SENTRY_REPO_UPSTREAM = os.environ.get("SENTRY_REPO_UPSTREAM", "getsentry/sentry")
SENTRY_REPO_WITH_PAT = repo_url_with_pat(SENTRY_REPO)
