#!/usr/bin/env python3

# This script is called in getsentry's gitbot.yml to ensure the integration between the two
from __future__ import annotations

import argparse
import logging
import os.path
import shutil
from tempfile import mkdtemp
from typing import Sequence

from gitbot.lib import bump_version, run

logging.getLogger().setLevel("DEBUG")
logging.basicConfig()

# TODO: replace b1ad2facd059465b344beb075037ecad0aa467bc with
#       merge sha of https://github.com/getsentry/sentry/pull/34879
_ref_sha="b1ad2facd059465b344beb075037ecad0aa467bc"

# TODO: also replace 4020db731c2d0be72b6df589e2e97859b92ad824
#       with another sentry sha ahead of b1ad2facd


def validate_bump(result: bool, text: str, temp_checkout: str) -> None:
    assert result is True

    assert text == f"Executed: bin/bump-sentry {_ref_sha}"
    execution = run("git show -s --oneline", temp_checkout)
    assert (
        "getsentry/sentry@ccc86db8a6a2541b5786f76e8461f587a8adca20" in execution.stdout
    ), execution.stdout
    execution = run("git grep ccc86db8a6a2541b5786f76e8461f587a8adca20", tmpdir)
    split_lines = execution.stdout.splitlines()
    assert split_lines == [
        "cloudbuild.yaml:            '--build-arg', 'SENTRY_VERSION_SHA=ccc86db8a6a2541b5786f76e8461f587a8adca20',",
        "docker/frontend_cloudbuild.yaml:      '--build-arg', 'SENTRY_VERSION_SHA=ccc86db8a6a2541b5786f76e8461f587a8adca20',",
        "sentry-version:ccc86db8a6a2541b5786f76e8461f587a8adca20",
    ], split_lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--branch",
        required=True,
        help="Branch to clone.",
    )
    parser.add_argument(
        "--getsentry-path",
        required=True,
        help="Path to getsentry checkout.",
    )
    args = parser.parse_args(argv)
    args.getsentry_path = os.path.abspath(args.getsentry_path)
    tmpdir = mkdtemp()
    temp_checkout = f"{tmpdir}/getsentry"
    try:
        # raise Exception()
        # We make a soft clone of it into a tempdir and then try to bump
        result, text = bump_version(
            branch=args.branch,
            ref_sha="ccc86db8a6a2541b5786f76e8461f587a8adca20",  # Random sha from Sentry repo
            url=args.getsentry_path,  # It will soft clone
            dry_run=True,  # This will prevent trying to push
            temp_checkout=temp_checkout,
            sentry_path=sentry_path,
        )
        validate_bump(result, text, temp_checkout)
    finally:
        # This undoes what bump version did
        run("git config --unset user.name", cwd=args.getsentry_path, raise_error=False)
        run("git config --unset user.email", cwd=args.getsentry_path, raise_error=False)
        shutil.rmtree(tmpdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
