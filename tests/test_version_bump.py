import os

from gitbot.lib import bump_command, bump_version, extract_author

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


def test_bump_command():
    assert bump_command("master", extract_author(event)) == [
        "tests/bin/bump-sentry",
        "master",
        "--author",
        expected_author,
    ]


def test_bump_version():
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
