import hmac
import hashlib
import logging
import os
import tempfile
import subprocess
from distutils import util

import sentry_sdk
from google.cloud import secretmanager
from flask import Flask, request, jsonify
from sentry_sdk.integrations.flask import FlaskIntegration

app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler())

IS_DEV = app.env == "development"

if not IS_DEV:
    ENV = os.environ.get("ENV", "production")
    app.logger.info(f"Environment: {ENV}")

    sentry_sdk.init(
        dsn="https://95cc5cfe034b4ff8b68162078978935c@o1.ingest.sentry.io/5748916",
        integrations=[FlaskIntegration()],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        environment=ENV,
    )

GETSENTRY_OWNER = "getsentry"
SENTRY_REPO = "{}/sentry".format(GETSENTRY_OWNER)

DEPLOY_MARKER = "#sync-getsentry"

PAT = os.environ.get("DEPLOY_SYNC_PAT")
# On GCR we use Google secrets to fetch the PAT
if not PAT:
    # If you're inside of GCR you don't need to set any env variables
    # If you want to test locally you will have to set GOOGLE_APPLICATION_CREDENTIALS to the path of the GCR key
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()
    # GCP project in which to store secrets in Secret Manager.
    response = client.access_secret_version(
        name="projects/sentry-dev-tooling/secrets/DeploySyncPat/versions/2"
    )
    PAT = response.payload.data.decode("UTF-8")
# This forces the production apps to explicitely have to set where to push
DEPLOY_REPO = os.environ["DEPLOY_REPO"]
DEPLOY_REPO_WITH_PAT = (
    f"https://{os.environ['DEPLOY_SYNC_USER']}:{PAT}@github.com/{DEPLOY_REPO}"
)
# XXX: Temp hard coding
SENTRY_REPO_WITH_PAT = f"https://{os.environ['DEPLOY_SYNC_USER']}:{PAT}@github.com/getsentry/getsentry-test-repo"
DEPLOY_BRANCH = "master"
COMMITTER_NAME = "Sentry Bot"
COMMITTER_EMAIL = "bot@getsentry.com"

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")

DRY_RUN = bool(util.strtobool(os.environ.get("DRY_RUN", "False")))
if DRY_RUN:
    app.logger.info("Dry run mode: on")
else:
    app.logger.info("Dry run mode: *OFF* <--!")
    app.logger.info(f"Code bumps will be pushed to {DEPLOY_BRANCH} on {DEPLOY_REPO}")


def run(*args, **kwargs):
    # XXX: The output of the clone command shows the PAT
    print(*args)
    kwargs.setdefault("timeout", 20)
    return subprocess.run(*args, **kwargs)


def respond(reason, updated=False):
    app.logger.info(reason)
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
            DEPLOY_REPO_WITH_PAT,
            repo_root,
            cwd=None,
        )
        != 0
    ):
        return False, "Cannot clone branch {} from {}.".format(branch, DEPLOY_REPO)

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
    app.logger.info(data)

    if data.get("ref") not in branches:
        app.logger.info(f'{data.get("ref")} not in {branches}')
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
            updated, reason = bump_version(DEPLOY_BRANCH, "bin/bump-sentry", *args)
        else:
            reason = "Unknown repository"

    return respond(reason=reason, updated=updated)


def process_pull_request():
    """Handle "pull_request" events from PRs with the deploy marker set"""
    data = request.get_json()
    app.logger.info(data)

    action = data.get("action")
    if action not in ["synchronize", "opened"]:
        app.logger.info(f"Action: '{action}' not in 'synchronize' or 'opened'")
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
    if body.find(DEPLOY_MARKER) == -1:
        return respond("Deploy marker not found.")

    ref_sha = head["sha"]
    branch = head["ref"]
    if ref_sha:
        # TODO: It would be ideal if we had a way to communicate back (repo or Slack)
        # that we did bump the version successfully
        updated, reason = bump_version(branch, "bin/bump-sentry", ref_sha)
        return respond(updated=updated, reason=reason)

    return respond("Commit not relevant for deploy sync.")


@app.route("/", methods=["POST"])
def index():
    if not IS_DEV:
        # Validate payload signature
        signature = hmac.new(
            GITHUB_WEBHOOK_SECRET.encode("utf-8"), request.data, hashlib.sha1
        ).hexdigest()
        if not hmac.compare_digest(
            signature,
            str(request.headers.get("X-Hub-Signature", "").replace("sha1=", "")),
        ):
            return respond(reason="Cannot validate payload signature.")

    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "push":
        return process_push()
    elif event_type == "pull_request":
        return process_pull_request()
    elif event_type == "revert":
        return process_sentry_revert()
    else:
        return respond("Unsupported event type.")


def process_sentry_revert():
    data = request.get_json()
    commit_to_revert = data["commit"]
    tmp_dir = tempfile.mkdtemp()

    reason = f"Failed to revert {commit_to_revert}"
    print(" ".join(["git", "clone", "-v", SENTRY_REPO_WITH_PAT]))
    foo = run(
        ["git", "clone", "-v", SENTRY_REPO_WITH_PAT],
        cwd=tmp_dir,
    )
    if foo.returncode == 0:
        repo_checkout = f"{tmp_dir}/getsentry-test-repo"
        run(["git", "revert", "-n", commit_to_revert], cwd=repo_checkout)
        run(["git", "push"], cwd=repo_checkout)
        return respond(reason=f"{commit_to_revert} reverted.", updated=True)

    return respond(reason=reason, updated=False)


@app.route("/eng-pipes", methods=["POST"])
def engPipes():
    event_type = request.headers.get("X-EngPipes-Event")

    if event_type == "revert":
        return process_sentry_revert()
    else:
        return respond("Unsupported event type.")


if not IS_DEV and not GITHUB_WEBHOOK_SECRET:
    raise SystemError("Empty GITHUB_WEBHOOK_SECRET!")
