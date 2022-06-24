from __future__ import annotations

import logging
import os
import subprocess

from gitbot.config import (
    LOGGING_LEVEL,
    PAT,
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
