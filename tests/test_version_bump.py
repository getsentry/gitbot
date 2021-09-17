from gitbot.lib import bump_command, bump_version, extract_author, run

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
    author = extract_author(event)
    assert author == expected_author
    assert bump_command("master", author) == [
        "bin/bump-sentry",
        "master",
        "--author",
        expected_author,
    ]


def test_bump_version():
    # XXX: Determine cwd
    toplevel = run(
        "git rev-parse --show-toplevel", cwd="/Users/armenzg/code/gitbot"
    ).stdout
    print(toplevel)
    bump_version(
        "armenzg/feat/fix",
        "9962ffff3d0b1973fb05e16cd6a3328c5ecb1401",
        extract_author(event),
        url=toplevel,
        dry_run=True,
    )
