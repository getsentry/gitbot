from unittest.mock import patch

from gitbot.lib import (
    bump_command,
    bump_sentry_path,
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
tests_bump_sentry_path = "tests/bin/bump-sentry"


def test_different_bump_sentry_path_with_env(monkeypatch):
    monkeypatch.setenv("GITBOT_BUMP_SENTRY_PATH", "different/path")
    assert bump_sentry_path() == "different/path"


@patch("gitbot.lib.bump_sentry_path")
def test_bump_command(mock_bump_path):
    mock_bump_path.return_value = tests_bump_sentry_path
    assert bump_command(ref_sha="foo") == [tests_bump_sentry_path, "foo"]
