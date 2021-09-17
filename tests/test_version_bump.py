import os

from gitbot.lib import bump_command, bump_version, extract_author

event = {
    "head_commit": {
        "author": {
            # fmt: off
            "name": 'Aniket Das "Tekky',
            # fmt: on
            "email": "85517732+AniketDas-Tekky@users.noreply.github.com",
            "username": "AniketDas-Tekky",
        },
    },
}

# fmt: off
expected_author = (
    'Aniket Das Tekky <85517732+AniketDas-Tekky@users.noreply.github.com>'
)
# fmt: on


def test_bump_command():
    assert bump_command("master", extract_author(event)) == [
        "bin/bump-sentry",
        "master",
        "--author",
        expected_author,
    ]


def test_bump_version():
    bump_version(
        "armenzg/feat/fix",
        "9962ffff3d0b1973fb05e16cd6a3328c5ecb1401",
        extract_author(event),
        # Path to gitbot checkout (i.e. Git top level dir)
        url=os.path.dirname(__file__).rsplit("/", 1)[0],
        dry_run=True,
    )
