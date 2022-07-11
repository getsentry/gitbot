#!/usr/bin/env python

# This script is called in getsentry's gitbot.yml to ensure the integration between the two
import argparse
import logging
import os
import shutil
from tempfile import mkdtemp

from gitbot.lib import bump_version, run

logging.getLogger().setLevel("DEBUG")
logging.basicConfig()


def validate_bump(result: bool, text: str, tmpdir: str) -> None:
    assert result is True
    # TODO: replace b1ad2facd059465b344beb075037ecad0aa467bc with
    #       merge sha of https://github.com/getsentry/sentry/pull/34879
    assert text == "Executed: bin/bump-sentry b1ad2facd059465b344beb075037ecad0aa467bc"
    execution = run("git show -s --oneline", tmpdir)
    assert (
        execution.stdout.find(
            "getsentry/sentry@b1ad2facd059465b344beb075037ecad0aa467bc"
        )
        > -1
    )
    execution = run("git grep b1ad2facd059465b344beb075037ecad0aa467bc", tmpdir)
    split_lines = execution.stdout.splitlines()
    assert len(split_lines) == 4
    for line in split_lines:
        assert (
            line.find("SENTRY_VERSION_SHA=b1ad2facd059465b344beb075037ecad0aa467bc")
            > -1
        )


def main(branch: str, getsentry_path: str, sentry_path: str) -> int:
    tmpdir = mkdtemp()
    try:
        # raise Exception()
        # We make a soft clone of it into a tempdir and then try to bump
        result, text = bump_version(
            branch=branch,
            ref_sha="ccc86db8a6a2541b5786f76e8461f587a8adca20",  # Random sha from Sentry repo
            url=getsentry_path,  # It will soft clone
            dry_run=True,  # This will prevent trying to push
            temp_checkout=tmpdir,  # We pass this value in order to inspect what happened
            sentry_path=sentry_path,
        )
        validate_bump(result, text, tmpdir)
    finally:
        # This undoes what bump version did
        run("git config --unset user.name", cwd=getsentry_path, raise_error=False)
        run("git config --unset user.email", cwd=getsentry_path, raise_error=False)
        shutil.rmtree(tmpdir)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--branch",
        type=str,
        help="Branch to clone.",
    )
    parser.add_argument(
        "--getsentry-path",
        type=str,
        help="Path to getsentry checkout.",
    )
    parser.add_argument(
        "--sentry-path",
        type=str,
        help="Path to sentry checkout.",
    )
    args = parser.parse_args()
    raise SystemExit(main(
        args.branch,
        os.path.abspath(args.getsentry_path),
        os.path.abspath(args.sentry_path),
    ))
