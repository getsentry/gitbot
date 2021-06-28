import logging
import subprocess

from config import *

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)


class CommandError(Exception):
    pass


def run(cmd: str, cwd: str = "/tmp", quiet: bool = False) -> object:
    # XXX: The output of the clone/push commands shows the PAT
    # GCR does not scrub the PAT. Sentry does
    new_cmd = None
    if isinstance(cmd, str):
        new_cmd = cmd.split()
        if ' "' in cmd:
            raise Exception(
                f"The command {cmd} contains double quotes. Pass a list instead of a string."
            )
    elif isinstance(cmd, list):
        new_cmd = cmd

    if not quiet:
        logger.info("> " + " ".join(new_cmd) + f" (cwd: {cwd})")

    # Capture the output so you can process it later and to show up in Sentry
    # Redirect stderr to stdout
    execution = subprocess.run(
        new_cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    output = ""
    if execution.stdout:
        for l in execution.stdout.splitlines():
            string = l.decode("utf-8")
            output += string
            if not quiet:
                logger.info(string)

    execution.stdout = output.strip()
    # If we raise an exception we will see it reported in Sentry and abort code execution
    if execution.returncode != 0:
        raise CommandError(output)
    return execution


def update_checkout(repo_url, checkout_path):
    logger.info(f"About to clone/pull {repo_url} to {checkout_path}.")
    if not os.path.exists(checkout_path):
        # We clone before the app is running. Requests will clone from this checkout
        run(f"git clone {repo_url} {checkout_path}")
        # This silences some Git hints. This is the recommended default setting
        run("git config pull.rebase false", cwd=checkout_path)

    # In case it was left in a bad state
    run("git fetch origin master", cwd=checkout_path)
    run("git reset --hard origin/master", cwd=checkout_path)
    run(f"git pull origin master", cwd=checkout_path)


def sync_with_upstream(checkout_path, upstream_url):
    """Fetch Git changes from upstream repo and push them to origin repo

    This helps to bring a test repo to be in sync withs related upstream repo.
    Useful for staging set up.
    """
    run(
        f"git remote get-url upstream || git remote add upstream {upstream_url}",
        cwd=checkout_path,
    )
    run("git fetch upstream master", cwd=checkout_path)
    run("git reset --hard upstream/master", cwd=checkout_path)
    run("git push -f origin master", cwd=checkout_path)


# Alias for updating the Sentry and Getsentry repos
def update_primary_repo(repo):
    if repo == "sentry":
        update_checkout(SENTRY_REPO_WITH_PAT, SENTRY_CHECKOUT_PATH)
    else:
        update_checkout(GETSENTRY_REPO_WITH_PAT, GETSENTRY_CHECKOUT_PATH)
