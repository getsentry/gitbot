from unittest.mock import patch

from gitbot.lib import (
    bump_command,
    bump_version,
    bump_sentry_path,
    extract_author,
    run,
)

event = {
    "head_commit": {
        "author": {
            "name": 'Aniket Das "Tekky',
            "email": "85517732+AniketDas-Tekky@users.noreply.github.com",
            "username": "AniketDas-Tekky",
        },
    },
}
expected_author = "Aniket Das Tekky <85517732+AniketDas-Tekky@users.noreply.github.com>"
tests_bump_sentry_path = "tests/bin/bump-sentry"


def test_different_bump_sentry_path_with_env(monkeypatch):
    monkeypatch.setenv("GITBOT_BUMP_SENTRY_PATH", "different/path")
    assert bump_sentry_path() == "different/path"


@patch("gitbot.lib.bump_sentry_path")
def test_bump_command(mock_bump_path):
    mock_bump_path.return_value = tests_bump_sentry_path
    assert bump_command(ref_sha="foo", author=extract_author(event)) == [
        tests_bump_sentry_path,
        "foo",
        "--author",
        expected_author,
    ]


@patch("gitbot.lib.bump_sentry_path")
def test_bump_command_no_author(mock_bump_path):
    mock_bump_path.return_value = tests_bump_sentry_path
    assert bump_command(ref_sha="foo") == [
        tests_bump_sentry_path,
        "foo",
    ]


# This test will fail if the user cannot checkout getsentry
# This test is executed by getsentry's CI
def test_real_bump_sentry_call(tmpdir):
    # We make a soft clone of it into a tempdir and then try to bump
    result, text = bump_version(
        branch="master",
        # Random sha from Sentry repo
        ref_sha="ccc86db8a6a2541b5786f76e8461f587a8adca20",
        # It will soft clone to a tempdir
        url="git@github.com:getsentry/getsentry.git",
        # This will prevent trying to push
        dry_run=True,
        temp_checkout=tmpdir,
        delete_temp_checkout=False,
    )
    assert result is True
    assert text == "Executed: bin/bump-sentry ccc86db8a6a2541b5786f76e8461f587a8adca20"
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
