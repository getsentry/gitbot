from __future__ import annotations

import hmac
import hashlib
import logging
import os
import tempfile
from operator import itemgetter
from typing import Any

import sentry_sdk

from flask import Flask, request, jsonify
from sentry_sdk.integrations.flask import FlaskIntegration

from gitbot.config import (
    COMMITTER_EMAIL,
    COMMITTER_NAME,
    DRY_RUN,
    ENV,
    GETSENTRY_BRANCH,
    GETSENTRY_CHECKOUT_PATH,
    GETSENTRY_REPO,
    GETSENTRY_REPO_URL,
    GITBOT_API_SECRET,
    GITHUB_WEBHOOK_SECRET,
    LOGGING_LEVEL,
    SENTRY_CHECKOUT_PATH,
    SENTRY_REPO,
    SENTRY_REPO_URL,
)
from gitbot.lib import (
    CommandError,
    run,
    update_checkout,
)

logging.basicConfig(
    level=LOGGING_LEVEL,
    # GCR logs already include the time
    format="%(message)s" if ENV == "development" else "%(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def boot() -> None:
    if ENV != "development":
        logger.info(f"Environment: {ENV}")
        logger.info(f"Release: {os.environ['RELEASE']}")
        sentry_sdk.init(
            dsn="https://95cc5cfe034b4ff8b68162078978935c@o1.ingest.sentry.io/5748916",
            integrations=[FlaskIntegration()],
            traces_sample_rate=1.0,
            environment=ENV,
            release=os.environ["RELEASE"],
            # These values are to hopefully help errors that did not report on time to Sentry
            # See https://github.com/getsentry/gitbot/pull/67 for details
            shutdown_timeout=10,
            transport_queue_size=1,
        )
        if not GITHUB_WEBHOOK_SECRET:
            raise SystemError("Empty GITHUB_WEBHOOK_SECRET!")
        if not GITBOT_API_SECRET:
            raise SystemError("Empty GITBOT_API_SECRET!")

    # Only the production instance is allowed to push to the real repos
    # We don't want more than one instance pushing to real repo by mistake
    if ENV != "production":
        assert SENTRY_REPO != "getsentry/sentry"
        assert GETSENTRY_REPO != "getsentry/getsentry"
    else:
        assert SENTRY_REPO == "getsentry/sentry"
        assert GETSENTRY_REPO == "getsentry/getsentry"

    os.environ["EMAIL"] = COMMITTER_EMAIL
    os.environ["GIT_AUTHOR_NAME"] = COMMITTER_NAME

    # This clones/updates the primary repos under /tmp
    if not os.environ.get("FAST_STARTUP"):
        update_primary_repo("sentry")
        update_primary_repo("getsentry")

    if DRY_RUN:
        logger.info("Dry run mode: on")
    else:
        logger.info("Dry run mode: *OFF* <--!")
        logger.info(
            f"Code bumps will be pushed to {GETSENTRY_BRANCH} on {GETSENTRY_REPO}"
        )


# Alias for updating the Sentry and Getsentry repos
def update_primary_repo(repo: str) -> None:
    quiet = LOGGING_LEVEL != "debug"
    if repo == "sentry":
        update_checkout(SENTRY_REPO_URL, SENTRY_CHECKOUT_PATH, quiet)
    else:
        update_checkout(GETSENTRY_REPO_URL, GETSENTRY_CHECKOUT_PATH, quiet)


def respond(data: str | dict[str, Any], status_code: int) -> tuple[str, int]:
    logger.info(data)
    if isinstance(data, str):
        data = {"reason": data}
    if status_code != 200:
        sentry_sdk.capture_message(data["reason"], "fatal")
    return jsonify(data), status_code


def valid_payload(secret: str, payload: bytes, signature: str) -> bool:
    # Validate payload signature
    payload_signature = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha1
    ).hexdigest()
    return hmac.compare_digest(payload_signature, signature)


boot()
app = Flask(__name__)


def process_git_revert() -> tuple[str, int]:
    data = request.get_json()
    repo, sha, name = itemgetter("repo", "sha", "name")(data)
    name = data["name"]
    logger.info(f"{name} has requested to revert {sha} from {repo}")

    tmp_dir = tempfile.mkdtemp()
    repo_url = SENTRY_REPO_URL if repo == "sentry" else GETSENTRY_REPO_URL
    checkout = SENTRY_CHECKOUT_PATH if repo == "sentry" else GETSENTRY_CHECKOUT_PATH

    # If there were multiple revert requests very close to each other there's a chance
    # that more than one `git pull` would be executed at the same time
    update_checkout(repo_url, checkout)

    # This avoids mutating the primary repo
    run(f"git clone {checkout} {tmp_dir}")
    execution = run(f'git log -1 --format="%s" {sha}', cwd=tmp_dir)
    # "fix(search): Correct a few types on the frontend grammar parser (#26554)"
    # "Revert "ref(snql) Update SDK to latest (#26638)""
    subject = execution.stdout.replace('"', "")
    if repo == "getsentry" and subject.startswith("getsentry/sentry@"):
        msg = f"{sha} cannot be reverted because it needs to be reverted in Sentry"
        return respond(msg, status_code=400)

    run(f"git revert --no-commit {sha}", cwd=tmp_dir)
    run(
        [
            "git",
            "commit",
            "-m",
            f'Revert "{subject}"',
            "-m",
            f"This reverts commit {sha}.",
            "-m",
            f"Co-authored-by: {name}",
        ],
        cwd=tmp_dir,
    )

    # Since we cloned from a local checkout we need to make sure to push to the remote repo
    push_args = f"git push {repo_url}"
    if DRY_RUN:
        push_args += " --dry-run"
    run(push_args, cwd=tmp_dir)
    revert_sha = run("git rev-parse origin/master", cwd=tmp_dir).stdout
    body = {"reason": f"{sha} reverted.", "revert_sha": revert_sha}
    return respond(body, status_code=200)


@app.route("/api/revert", methods=["POST"])
def revert() -> tuple[str, int]:
    if GITBOT_API_SECRET and not valid_payload(
        GITBOT_API_SECRET,
        request.data,
        str(request.headers.get("X-Signature", "").replace("sha1=", "")),
    ):
        return respond("Cannot validate payload signature.", status_code=403)

    try:
        return process_git_revert()
    except CommandError as e:
        sentry_sdk.capture_exception(e)
        logger.exception(e)
        return respond("Failed to revert.", status_code=400)
