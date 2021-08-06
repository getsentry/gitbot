# Generic name since the names of the source code is needs some refactoring first
from gitbot.lib import extract_author

event = {
    "head_commit": {
        "author": {
            "name": 'Aniket Das "Tekky',
            "email": "85517732+AniketDas-Tekky@users.noreply.github.com",
            "username": "AniketDas-Tekky",
        },
    },
}


def test_extract_author():
    author = extract_author(event)
    assert (
        author == "Aniket Das Tekky <85517732+AniketDas-Tekky@users.noreply.github.com>"
    )


def test_bump_command():
    bump_command("master", extract_author(event))
