import logging
import os
import subprocess

from gitbot.config import LOGGING_LEVEL, PAT

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)


class CommandError(Exception):
    pass


def run(cmd: str, cwd: str = "/tmp", quiet: bool = False) -> object:
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
    scrub_output = PAT not in new_cmd
    if not quiet:
        _command = "> " + " ".join(new_cmd) + f" (cwd: {cwd})"
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


def update_checkout(repo_url, checkout_path):
    logger.info(f"About to clone/pull to {checkout_path}.")
    if not os.path.exists(checkout_path):
        # We clone before the app is running. Requests will clone from this checkout
        run(f"git clone {repo_url} {checkout_path}")
        # This silences some Git hints. This is the recommended default setting
        run("git config pull.rebase false", cwd=checkout_path)

    # In case it was left in a bad state
    run("git fetch origin master", cwd=checkout_path)
    run("git reset --hard origin/master", cwd=checkout_path)
    run("git pull origin master", cwd=checkout_path)


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
    # Drop quote
    # Aniket Das "Tekky <85517732+AniketDas-Tekky@users.noreply.github.com>
    # Aniket Das Tekky <85517732+AniketDas-Tekky@users.noreply.github.com>
    author_name = author_data.get("name").replace('"', "")
    author_email = author_data.get("email")
    if author_name and author_email:
        author = f"{author_name} <{author_email}>"
    else:
        author = None
    return author
