from __future__ import annotations

import contextlib
import logging
import os
import shlex
import subprocess
import tempfile
from typing import Any

from gitbot.config import (
    COMMITTER_EMAIL,
    COMMITTER_NAME,
    DRY_RUN,
    GETSENTRY_REPO_URL,
    GETSENTRY_REPO,
    LOGGING_LEVEL,
    PAT,
    SENTRY_BRANCH,
    SENTRY_REPO,
    SENTRY_REPO_URL,
)

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)


class CommandError(Exception):
    pass


def run(
    cmd: str | list[str],
    cwd: str = "/tmp",
    quiet: bool = False,
    raise_error: bool = True,
) -> subprocess.CompletedProcess[str]:
    if isinstance(cmd, str):
        new_cmd = cmd.split()
        if ' "' in cmd:
            raise Exception(
                f"The command {cmd} contains double quotes. Pass a list instead of a string."
            )
    elif isinstance(cmd, list):
        new_cmd = cmd
    else:
        raise TypeError(f"expected str/list got: {cmd=}")

    # GCR does not scrub the Personal Access Token from the output
    scrub_output = PAT and PAT not in new_cmd
    if not quiet:
        _command = "> "
        for part in new_cmd:
            if " " in part:
                _command += f' "{part}"'
            else:
                _command += f" {part}"
        _command += f" (cwd: {cwd})"
        if scrub_output and PAT is not None:
            _command = _command.replace(PAT, "<secret>")
        logger.info(_command)

    # Capture the output so you can process it later and to show up in Sentry
    # Redirect stderr to stdout
    execution = subprocess.run(
        new_cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="UTF-8",
    )

    output = ""
    if execution.stdout:
        for string in execution.stdout.splitlines():
            if scrub_output and PAT is not None:
                string = string.replace(PAT, "<secret>")
            output += f"{string}\n"
            if not quiet:
                logger.info(string)

    execution.stdout = output.strip()
    # If we raise an exception we will see it reported in Sentry and abort code execution
    if execution.returncode != 0 and raise_error:
        raise CommandError(output)
    return execution


def update_checkout(repo_url: str, checkout_path: str, quiet: bool = False) -> None:
    logger.info(f"About to clone/pull {repo_url} to {checkout_path}.")
    if not os.path.exists(checkout_path):
        # We clone before the app is running. Requests will clone from this checkout
        run(f"git clone {repo_url} {checkout_path}", quiet=quiet)
        # This silences some Git hints. This is the recommended default setting
        run("git config pull.rebase false", cwd=checkout_path, quiet=quiet)

    # In case it was left in a bad state
    run("git fetch origin master", cwd=checkout_path, quiet=quiet)
    run("git reset --hard origin/master", cwd=checkout_path, quiet=quiet)
    run("git pull origin master", cwd=checkout_path, quiet=quiet)


def sync_with_upstream(checkout_path: str, upstream_url: str) -> None:
    """Fetch Git changes from upstream repo and push them to origin repo

    This helps to bring a test repo to be in sync withs related upstream repo.
    Useful for staging set up.
    """
    try:
        run("git remote get-url upstream", cwd=checkout_path)
    except CommandError:
        run(f"git remote add upstream {upstream_url}", cwd=checkout_path)

    run("git fetch upstream master", cwd=checkout_path)
    run("git reset --hard upstream/master", cwd=checkout_path)
    run("git push -f origin master", cwd=checkout_path)


def extract_author(data: dict[str, Any]) -> str | None:
    author_data = data.get("head_commit", {}).get("author", {})
    author_name = author_data.get("name")
    author_email = author_data.get("email")
    if author_name and author_email:
        author = f"{author_name} <{author_email}>"
    else:
        author = None
    return author


def bump_sentry_path() -> str:
    # Allowing changing this via the env variable will allow the getsentry repo to test
    # changes to the official file
    return os.environ.get("GITBOT_BUMP_SENTRY_PATH", "bin/bump-sentry")


def bump_command(ref_sha: str, author: str | None = None) -> list[str]:
    cmd = [bump_sentry_path(), ref_sha]
    # Original author will be displayed as author in getsentry/getsentry commits
    if author is not None:
        # fmt: off
        cmd += ["--author", author.replace('"', '')]
        # fmt: on
    return cmd


def bump_version(
    branch: str,
    ref_sha: str,
    author: str | None = None,
    url: str = GETSENTRY_REPO_URL,
    dry_run: bool = DRY_RUN,
    temp_checkout: str | None = None,
) -> tuple[bool, str]:
    with contextlib.ExitStack() as ctx:
        if temp_checkout is not None:
            repo_root = temp_checkout
        else:
            # Once we exit the with statement the temporary directory witll be deleted
            repo_root = ctx.enter_context(tempfile.TemporaryDirectory())

        # The branch has to exist in the remote repo
        try:
            run(
                f"git clone --depth 1 -b {branch} {url} {repo_root}",
                cwd=repo_root,
            )
        except CommandError:
            return False, f"Cannot clone branch {branch} from {GETSENTRY_REPO}.\nError: {e}"

        # Checkout the desired sentry branch.
        try:
            run(
                f"git -C ../sentry checkout {SENTRY_BRANCH}",
                cwd=repo_root,
            )
        except CommandError as e:
            return False, f"Cannot checkout branch {SENTRY_BRANCH} from {SENTRY_REPO}.\nError: {e}"

        run(f"git config user.name {COMMITTER_NAME}", cwd=repo_root)
        run(f"git config user.email {COMMITTER_EMAIL}", cwd=repo_root)

        try:
            # meh ref_sha won't have the necessary stuff...
            # needs to be SENTRY_BRANCH temporarily, i just need to test the codepath
            command = bump_command(SENTRY_BRANCH, author)
            run(command, cwd=repo_root)
        except CommandError:
            execution = run("git show", cwd=repo_root)
            # e.g. https://github.com/getsentry/getsentry/pull/7672/commits
            if execution.stdout.find(f"getsentry/sentry@{ref_sha}") > -1:
                logger.info("The developer has manually bumped the version.")
            else:
                raise

        if dry_run:
            push_cmd = f"git push origin --dry-run {branch}"
        else:
            push_cmd = f"git push origin {branch}"
        successful_push = False
        for _ in range(5):
            try:
                run(push_cmd, cwd=repo_root)
                successful_push = True
                break
            except CommandError:
                run(f"git pull --rebase origin {branch}", cwd=repo_root)

        if not successful_push:
            return False, "Failed to push."
        else:
            return True, f"Executed: {shlex.join(command)}"

    raise AssertionError("unreachable")
