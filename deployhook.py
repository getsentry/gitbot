import hmac
import hashlib
import os
import tempfile
import subprocess
from distutils import util
from contextlib import contextmanager
from flask import Flask, request, jsonify

app = Flask(__name__)

IS_DEV = app.env == "development"

GETSENTRY_OWNER = "getsentry"
SENTRY_REPO = "{}/sentry".format(GETSENTRY_OWNER)

DEPLOY_MARKER = "#sync-getsentry"

DEPLOY_REPO = os.environ.get("DEPLOY_REPO", "git@github.com:getsentry/getsentry")
DEPLOY_BRANCH = "master"
COMMITTER_NAME = "Sentry Bot"
COMMITTER_EMAIL = "bot@getsentry.com"

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")

DRY_RUN = not bool(util.strtobool(os.environ.get("DRY_RUN", False)))
if DRY_RUN:
    app.logger.info("Dry run mode: on")
else:
    app.logger.info("Dry run mode: *OFF* <--!")
    app.logger.info(f"Code bumps will be pushed to {DEPLOY_BRANCH} on {DEPLOY_REPO}")


def bump_version(branch, script, *args):
    repo_root = tempfile.mkdtemp()

    def cmd(*args, **opts):
        opts.setdefault("cwd", repo_root)
        try:
            app.logger.info(" ".join(args))
        except Exception:
            # XXX: Report via Sentry later on
            app.logger.warning("Investigate why we could not log the args.")
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
            DEPLOY_REPO,
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
    # On what occassions would we want to use request.args.get("branches")?
    # Pushes to master and test-branch will be acted on
    branches = set(
        "refs/heads/" + x for x in (request.args.get("branches") or "master,test-branch").split(",")
    )

    data = request.get_json()
    app.logger.info(data)

    if data.get("ref") not in branches:
        app.logger.info(f'{data.get("ref")} not in {branches}')
        return jsonify(updated=False, reason="Commit against untracked branch.")

    repo = data["repository"]["full_name"]
    head_commit = data.get("head_commit", {})
    ref_sha = head_commit.get("id")

    # Original author will be displayed as author in getsentry/getsentry
    author_data = head_commit.get("author", {})
    author_name = author_data.get("name")
    author_email = author_data.get("email")
    if author_name and author_email:
        author = u"{} <{}>".format(author_name, author_email).encode("utf8")
    else:
        author = None

    if ref_sha is not None:
        args = [ref_sha]
        if author is not None:
            args += ["--author", author]

        # Support Sentry fork when running on development mode
        if (not IS_DEV and repo == SENTRY_REPO) or (IS_DEV and data["repository"]["name"] == "sentry"):
            updated, reason = bump_version(DEPLOY_BRANCH, "bin/bump-sentry", *args)
        else:
            updated = False
            reason = "Unknown repository"
        app.logger.info(f"We found some issues: {reason}")
        return jsonify(updated=updated, reason=reason)

    return jsonify(updated=False, reason="Commit not relevant for deploy sync.")


def process_pull_request():
    """Handle "pull_request" events from PRs with the deploy marker set"""
    data = request.get_json()

    if data.get("action") not in ["synchronize", "opened"]:
        return jsonify(updated=False, reason="Invalid action for pull_request event.")

    if data["repository"]["full_name"] != SENTRY_REPO:
        return jsonify(updated=False, reason="Unknown repository")

    # Check that the PR is from the same repo
    pull_request = data["pull_request"]
    head = pull_request["head"]
    base = pull_request["base"]
    if (
        head["repo"]["full_name"] != SENTRY_REPO
        or base["repo"]["full_name"] != SENTRY_REPO
    ):
        return jsonify(updated=False, reason="Invalid head or base repos.")

    if pull_request["merged"]:
        return jsonify(updated=False, reason="Pull request is already merged.")

    body = pull_request["body"] or ""
    if body.find(DEPLOY_MARKER) == -1:
        return jsonify(updated=False, reason="Deploy marker not found.")

    ref_sha = head["sha"]
    branch = head["ref"]
    if ref_sha:
        updated, reason = bump_version(branch, "bin/bump-sentry", ref_sha)
        return jsonify(updated=updated, reason=reason)

    return jsonify(updated=False, reason="Commit not relevant for deploy sync.")


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
            return jsonify(updated=False, reason="Cannot validate payload signature.")

    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "push":
        return process_push()
    elif event_type == "pull_request":
        return process_pull_request()
    else:
        return jsonify(updated=False, reason="Unsupported event type.")

if not app.debug:
    import logging

    app.logger.addHandler(logging.StreamHandler())

if not IS_DEV and not GITHUB_WEBHOOK_SECRET:
    raise SystemError("Empty GITHUB_WEBHOOK_SECRET!")
