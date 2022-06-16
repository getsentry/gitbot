import logging
import os
import subprocess
import tempfile

from gitbot.config import (
    COMMITTER_EMAIL,
    COMMITTER_NAME,
    DRY_RUN,
    GETSENTRY_REPO_URL,
    GETSENTRY_REPO,
    LOGGING_LEVEL,
    PAT,
)

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)


class CommandError(Exception):
    pass


def run(cmd, cwd: str = "/tmp", quiet: bool = False) -> object:
    new_cmd = None
    if isinstance(cmd, str):
        new_cmd = cmd.split()
        if ' "' in cmd:
            raise Exception(
                f"The command {cmd} contains double quotes. Pass a list instead of a string."
            )
    elif isinstance(cmd, list):
        new_cmd = cmd

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
        if scrub_output:
            _command = _command.replace(PAT, "<secret>")
        logger.info(_command)

    # Capture the output so you can process it later and to show up in Sentry
    # Redirect stderr to stdout
    execution = subprocess.run(
        new_cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    output = ""
    if execution.stdout:
        for line in execution.stdout.splitlines():
            string = line.decode("utf-8")
            if scrub_output:
                string = string.replace(PAT, "<secret>")
            output += f"{string}\n"
            if not quiet:
                logger.info(string)

    execution.stdout = output.strip()
    # If we raise an exception we will see it reported in Sentry and abort code execution
    if execution.returncode != 0:
        raise CommandError(output)
    return execution


def update_checkout(repo_url, checkout_path, quiet=False):
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


def sync_with_upstream(checkout_path, upstream_url):
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


def extract_author(data):
    author_data = data.get("head_commit", {}).get("author", {})
    author_name = author_data.get("name")
    author_email = author_data.get("email")
    if author_name and author_email:
        author = f"{author_name} <{author_email}>"
    else:
        author = None
    return author


def bump_sentry_path():
    # Allowing changing this via the env variable will allow the getsentry repo to test
    # changes to the official file
    return os.environ.get("GITBOT_BUMP_SENTRY_PATH", "bin/bump-sentry")


def bump_command(ref_sha, author=None):
    cmd = [bump_sentry_path(), ref_sha]
    # Original author will be displayed as author in getsentry/getsentry commits
    if author is not None:
        # fmt: off
        cmd += ["--author", author.replace('"', '')]
        # fmt: on
    return cmd


def bump_version(
    branch,
    ref_sha,
    author=None,
    url=GETSENTRY_REPO_URL,
    dry_run=DRY_RUN,
    temp_checkout=tempfile.mkdtemp(),
    delete_temp_checkout=True,
):
    repo_root = temp_checkout

    # The branch has to be created manually in getsentry/getsentry!
    try:
        run(
            f"git clone --depth 1 -b {branch} {url} {repo_root}",
            cwd=repo_root,
        )
    except CommandError:
        return False, "Cannot clone branch {} from {}.".format(branch, GETSENTRY_REPO)

    run(f"git config user.name {COMMITTER_NAME}", cwd=repo_root)
    run(f"git config user.email {COMMITTER_EMAIL}", cwd=repo_root)

    command = bump_command(ref_sha, author)
    run(command, cwd=repo_root)

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

    if delete_temp_checkout:
        os.rmdir(repo_root)

    if not successful_push:
        return False, "Failed to push."
    else:
        return True, f"Executed: {' '.join(command)}"
