from unittest.mock import patch
import os

from gitbot.lib import (
    bump_command,
    bump_version,
    bump_sentry_path,
    extract_author,
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


@patch("gitbot.lib.bump_sentry_path")
def test_bump_version(mock_bump_path):
    mock_bump_path.return_value = tests_bump_sentry_path
    # This will checkout gitbot in a tempdir and try calling bin/bump-sentry
    bump_version(
        "master",
        # Any valid sha is good enough
        "9962ffff3d0b1973fb05e16cd6a3328c5ecb1401",
        extract_author(event),
        # Path to gitbot checkout (i.e. Git top level dir)
        url=os.path.dirname(__file__).rsplit("/", 1)[0],
        dry_run=True,
    )
