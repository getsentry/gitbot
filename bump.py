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

# TODO: replace 4020db731c2d0be72b6df589e2e97859b92ad824 with
#       merge sha of https://github.com/getsentry/sentry/pull/34879
_ref_sha = "4020db731c2d0be72b6df589e2e97859b92ad824"


def validate_bump(result: bool, text: str, temp_checkout: str) -> None:
    assert result is True

    assert text == f"Executed: bin/bump-sentry {_ref_sha}"
    execution = run("git show -s --oneline", temp_checkout)
    assert (
        f"getsentry/sentry@{_ref_sha}" in execution.stdout
    ), execution.stdout
    execution = run(f"git grep {_ref_sha}", temp_checkout)
    split_lines = execution.stdout.splitlines()
    assert split_lines == [
        f"cloudbuild.yaml:            '--build-arg', 'SENTRY_VERSION_SHA={_ref_sha}',",
        f"docker/frontend_cloudbuild.yaml:      '--build-arg', 'SENTRY_VERSION_SHA={_ref_sha}',",
        f'sentry-requirements-dev-frozen.txt:# DO NOT MODIFY. This file was generated with `python -m bin.bump_sentry {_ref_sha}`.',
        f'sentry-requirements-frozen.txt:# DO NOT MODIFY. This file was generated with `python -m bin.bump_sentry {_ref_sha}`.',
        f'sentry-version:{_ref_sha}',
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
    parser.add_argument(
        "--sentry-path",
        type=str,
        help="Path to sentry checkout.",
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
            ref_sha=_ref_sha,  # Random sha from Sentry repo
            url=args.getsentry_path,  # It will soft clone
            dry_run=True,  # This will prevent trying to push
            temp_checkout=temp_checkout,
            sentry_path=args.sentry_path,
        )
        validate_bump(result, text, temp_checkout)
    finally:
        # This undoes what bump version did
        run("git config --unset user.name", cwd=temp_checkout, raise_error=False)
        run("git config --unset user.email", cwd=temp_checkout, raise_error=False)
        shutil.rmtree(tmpdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
