import hmac
import hashlib
import logging
import tempfile
import subprocess

import sentry_sdk

from flask import Flask, request, jsonify
from sentry_sdk.integrations.flask import FlaskIntegration

from config import *

logging.basicConfig(
    level=LOGGING_LEVEL,
    # GCR logs already include the time
    format="%(asctime)s %(levelname)-8s %(message)s"
    if ENV == "development"
    else "%(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

if ENV != "development":
    logger.info(f"Environment: {ENV}")
    sentry_sdk.init(
        dsn="https://95cc5cfe034b4ff8b68162078978935c@o1.ingest.sentry.io/5748916",
        integrations=[FlaskIntegration()],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        environment=ENV,
    )
    if not GITHUB_WEBHOOK_SECRET:
        raise SystemError("Empty GITHUB_WEBHOOK_SECRET!")

# Only the production instance is allowed to push to the real repos
# We don't want more than one instance pushing to real repo by mistake
if ENV != "production":
    assert SENTRY_REPO != "getsentry/sentry"
    assert GETSENTRY_REPO != "getsentry/getsentry"
else:
    assert SENTRY_REPO == "getsentry/sentry"
    assert GETSENTRY_REPO == "getsentry/getsentry"


app = Flask(__name__)


if DRY_RUN:
    logger.info("Dry run mode: on")
else:
    logger.info("Dry run mode: *OFF* <--!")
    logger.info(f"Code bumps will be pushed to {GETSENTRY_BRANCH} on {GETSENTRY_REPO}")


def respond(reason, updated=False):
    logger.info(reason)
    return jsonify(updated=updated, reason=reason)


def bump_version(branch, script, *args):
    repo_root = tempfile.mkdtemp()

    def cmd(*args, **opts):
        # Do not show the output of the git clone command since the PAT shows in the output
        opts.setdefault("cwd", repo_root)
        return subprocess.Popen(list(args), **opts).wait()

    # The branch has to be created manually in getsentry/getsentry!
    if (
        cmd(
            "git",
            "clone",
            "--depth",
            "1",
            "-b",
            branch,
            GETSENTRY_REPO_WITH_PAT,
            repo_root,
            cwd=None,
        )
        != 0
    ):
        return False, "Cannot clone branch {} from {}.".format(branch, GETSENTRY_REPO)

    cmd("git", "config", "user.name", COMMITTER_NAME)
    cmd("git", "config", "user.email", COMMITTER_EMAIL)
    cmd(script, *args)
    push_args = None
    if DRY_RUN:
        push_args = ("git", "push", "origin", "--dry-run", branch)
    else:
        push_args = ("git", "push", "origin", branch)
    for _ in range(5):
        if cmd(*push_args) == 0:
            break
        cmd("git", "pull", "--rebase", "origin", branch)

    return True, "Executed: {!r}".format([script] + list(args))


def process_push():
    """Handle "push" events to master branch"""
    # XXX: On what occassions would we want to use request.args.get("branches")?
    # Pushes to master and test-branch will be acted on
    branches = set(
        f"refs/heads/{x}"
        for x in (request.args.get("branches") or "master,test-branch").split(",")
    )

    data = request.get_json()
    logger.info(data)

    if data.get("ref") not in branches:
        logger.info(f'{data.get("ref")} not in {branches}')
        return respond("Commit against untracked branch.")

    repo = data["repository"]["full_name"]
    head_commit = data.get("head_commit", {})
    ref_sha = head_commit.get("id")

    # Original author will be displayed as author in getsentry/getsentry
    author_data = head_commit.get("author", {})
    author_name = author_data.get("name")
    author_email = author_data.get("email")
    if author_name and author_email:
        author = f"{author_name} <{author_email}>"
    else:
        author = None

    updated = False
    reason = "Commit not relevant for deploy sync."
    if ref_sha is not None:
        args = [ref_sha]
        if author is not None:
            args += ["--author", author]

        # Support Sentry fork when running on development mode
        if (IS_DEV and repo.split("/")[1] == "sentry") or (repo == SENTRY_REPO):
            updated, reason = bump_version(GETSENTRY_BRANCH, "bin/bump-sentry", *args)
        else:
            reason = "Unknown repository"

    return respond(reason=reason, updated=updated)


def process_pull_request():
    """Handle "pull_request" events from PRs with the deploy marker set"""
    data = request.get_json()
    logger.info(data)

    action = data.get("action")
    if action not in ["synchronize", "opened"]:
        logger.info(f"Action: '{action}' not in 'synchronize' or 'opened'")
        return respond("Invalid action for pull_request event.")

    # Check that the PR is from the same repo
    pull_request = data["pull_request"]
    head = pull_request["head"]
    base = pull_request["base"]

    # No need to make all these checks if we're in development
    if not IS_DEV:
        if data["repository"]["full_name"] != SENTRY_REPO:
            return respond("Unknown repository")

        if (
            head["repo"]["full_name"] != SENTRY_REPO
            or base["repo"]["full_name"] != SENTRY_REPO
        ):
            return respond("Invalid head or base repos.")

        if pull_request["merged"]:
            return respond("Pull request is already merged.")

    body = pull_request["body"] or ""
    if body.find(GITBOT_MARKER) == -1:
        return respond("Deploy marker not found.")

    ref_sha = head["sha"]
    branch = head["ref"]
    if ref_sha:
        # TODO: It would be ideal if we had a way to communicate back (repo or Slack)
        # that we did bump the version successfully
        updated, reason = bump_version(branch, "bin/bump-sentry", ref_sha)
        return respond(updated=updated, reason=reason)

    return respond("Commit not relevant for deploy sync.")


def valid_payload(secret: str, payload: str, signature: str) -> bool:
    # Validate payload signature
    payload_signature = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha1
    ).hexdigest()
    return hmac.compare_digest(payload_signature, signature)


@app.route("/", methods=["POST"])
def index():
    if GITHUB_WEBHOOK_SECRET and not valid_payload(
        GITHUB_WEBHOOK_SECRET,
        request.data,
        str(request.headers.get("X-Hub-Signature", "").replace("sha1=", "")),
    ):
        return respond(reason="Cannot validate payload signature.")

    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "push":
        return process_push()
    elif event_type == "pull_request":
        return process_pull_request()
    else:
        return respond("Unsupported event type.")
