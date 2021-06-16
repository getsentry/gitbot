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


class CommandError(Exception):
    pass


def run(*args, **kwargs):
    # XXX: The output of the clone/push commands shows the PAT
    # GCR does not scrub the PAT. Sentry does
    print(" ".join(*args))
    # Redirect stderr to stdout
    execution = subprocess.run(
        *args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    for l in execution.stdout.splitlines():
        print(l)
    print(f"return code: {execution.returncode}")
    # If we raise an exception we will see it reported in Sentry and abort code execution
    if execution.returncode != 0:
        raise CommandError
    return execution


# ENV is defined for staging/production
ENV = os.environ.get("FLASK_ENV") or os.environ["ENV"]
# This variable is only used during local development
if not ENV == "development":
    print(f"Environment: {ENV}")

    sentry_sdk.init(
        dsn="https://95cc5cfe034b4ff8b68162078978935c@o1.ingest.sentry.io/5748916",
        integrations=[FlaskIntegration()],
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        environment=ENV,
    )

DEPLOY_BRANCH = "master"
DEPLOY_MARKER = "#sync-getsentry"
COMMITTER_NAME = "Sentry Bot"
COMMITTER_EMAIL = "bot@getsentry.com"

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
SENTRY_REPO = os.environ.get("SENTRY_REPO", "getsentry/sentry")
SENTRY_REPO_WITH_PAT = (
    f"https://{os.environ['DEPLOY_SYNC_USER']}:{PAT}@github.com/{SENTRY_REPO}"
)
SENTRY_CHECKOUT = "/tmp/{}".format(SENTRY_REPO.split("/")[-1])
if not os.path.exists(SENTRY_CHECKOUT):
    # XXX: If this fails we will be in a bad state. Put effort into recovery or other method
    # to pump the checkout
    # We clone before the app is running. We will be cloning from this checkout
    run(["git", "clone", SENTRY_REPO_WITH_PAT, SENTRY_CHECKOUT])
else:
    run(["git", "clean", "-f"], cwd=SENTRY_CHECKOUT)
    run(["git", "pull"], cwd=SENTRY_CHECKOUT)


app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler())

IS_DEV = app.env == "development"

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")

DRY_RUN = bool(util.strtobool(os.environ.get("DRY_RUN", "False")))
if DRY_RUN:
    app.logger.info("Dry run mode: on")
else:
    app.logger.info("Dry run mode: *OFF* <--!")
    app.logger.info(f"Code bumps will be pushed to {DEPLOY_BRANCH} on {DEPLOY_REPO}")

# Make sure that doing development/staging will not push to the real repos
if ENV != "production":
    assert SENTRY_REPO != "getsentry/sentry"
    assert DEPLOY_REPO != "getsentry/getsentry"


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
    else:
        return respond("Unsupported event type.")


def process_git_revert():
    data = request.get_json()
    commit_to_revert = data["commit"]
    name = data["name"]
    print(f"{name} has requested to revert {commit_to_revert}")

    tmp_dir = tempfile.mkdtemp()
    try:
        # We clone from a local checkout to speed up the first cloning and since we have threading
        # we should not be touching the first checkout unless we can guarantee thread safety
        run(["git", "clone", SENTRY_CHECKOUT, tmp_dir])
        # The local checkout falls out of date, thus, we need to pull new changes
        run(["git", "pull"], cwd=tmp_dir)
        # For now, we're making this local but eventually we should use this globally
        env = {
            "GIT_AUTHOR_NAME": "getsentry-bot",
            "EMAIL": "bot@sentry.io",
        }
        run(["git", "revert", "--no-edit", commit_to_revert], cwd=tmp_dir, env=env)

        # Since we cloned from a local checkout we need to make sure to push to the remote repo
        push_args = ["git", "push", SENTRY_REPO_WITH_PAT]
        if DRY_RUN:
            push_args.append("--dry-run")
        run(push_args, cwd=tmp_dir, env=env)
        return respond(reason=f"{commit_to_revert} reverted.", updated=True)
    except CommandError as e:
        sentry_sdk.capture_exception(e)
        print(e)
        return respond(reason=f"Failed to revert {commit_to_revert}", updated=False)


@app.route("/api/revert", methods=["POST"])
def revert():
    return process_git_revert()


if not IS_DEV and not GITHUB_WEBHOOK_SECRET:
    raise SystemError("Empty GITHUB_WEBHOOK_SECRET!")
