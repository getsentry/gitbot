# Generic name since the names of the source code is needs some refactoring first
from gitbot.lib import bump_command, extract_author

event = {
    "head_commit": {
        "author": {
            "name": 'Aniket Das "Tekky',
            "email": "85517732+AniketDas-Tekky@users.noreply.github.com",
            "username": "AniketDas-Tekky",
        },
    },
}

# fmt: off
expected_author = (
    'Aniket Das \"Tekky <85517732+AniketDas-Tekky@users.noreply.github.com>'
)
# fmt: on


def test_bump_command():
    assert bump_command("master", extract_author(event)) == [
        "bin/bump-sentry",
        "master",
        "--author",
        expected_author,
    ]
