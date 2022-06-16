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


def main(branch, getsentry_path):
    tmpdir = mkdtemp()
    try:
        # We make a soft clone of it into a tempdir and then try to bump
        result, text = bump_version(
            branch=branch,
            # Random sha from Sentry repo
            ref_sha="ccc86db8a6a2541b5786f76e8461f587a8adca20",
            # It will soft clone to a tempdir
            url=getsentry_path,
            # This will prevent trying to push
            dry_run=True,
            temp_checkout=tmpdir,
            delete_temp_checkout=False,
        )
        # print(execution.stdout)
        assert result is True
        assert (
            text == "Executed: bin/bump-sentry ccc86db8a6a2541b5786f76e8461f587a8adca20"
        )
        execution = run("git show -s --oneline", tmpdir)
        assert (
            execution.stdout.find(
                "getsentry/sentry@ccc86db8a6a2541b5786f76e8461f587a8adca20"
            )
            > -1
        )
        execution = run("git grep ccc86db8a6a2541b5786f76e8461f587a8adca20", tmpdir)
        split_lines = execution.stdout.splitlines()
        assert len(split_lines) == 4
        for line in split_lines:
            assert (
                line.find("SENTRY_VERSION_SHA=ccc86db8a6a2541b5786f76e8461f587a8adca20")
                > -1
            )
    finally:
        shutil.rmtree(tmpdir)


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
    args = parser.parse_args()
    raise SystemExit(main(args.branch, os.path.abspath(args.getsentry_path)))
