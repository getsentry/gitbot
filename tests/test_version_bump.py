from gitbot.deployhook import bump_version
from gitbot.lib import bump_command, extract_author, run

CHECKOUT_ROOT_PATH = __file__.rsplit("/", 2)[0]

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
    'Aniket Das Tekky <85517732+AniketDas-Tekky@users.noreply.github.com>'
)
# fmt: on


class TestBump:
    def test_bump_command(self):
        assert bump_command("master", extract_author(event)) == [
            "bin/bump-sentry",
            "master",
            "--author",
            expected_author,
        ]

    # XXX: Move the checking out of the repo into a fixture
    def test_bump_version(self, tmpdir):
        new_checkout = tmpdir
        run(f"git clone --depth 1 {CHECKOUT_ROOT_PATH} {new_checkout}")
        bump_version("master", "master", extract_author(event), url=new_checkout)
