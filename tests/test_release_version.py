import time
from gitbot.lib import run

# XXX: Common logic move somewhere else
CHECKOUT_ROOT_PATH = __file__.rsplit("/", 2)[0]


def test_release_version(tmpdir):
    # XXX: This code needs to be turned into a fixture
    new_checkout = tmpdir
    run(f"git clone --depth 1 {CHECKOUT_ROOT_PATH} {new_checkout}")
    run("git log -5 --oneline", cwd=new_checkout)
    run("git checkout 65174614f6109df4264febaf96b87b52b89d0ffe", cwd=new_checkout)
    version = run("./release_version.sh", cwd=new_checkout).stdout
    # XXX: Adjust the version once it lands on master
    assert version in (
        "2021.8.20+095555.armenzg-semver.6517461",
        "2021.8.20+095555.HEAD.6517461",
    )
    # The release version should be idempotent
    time.sleep(3)
    version = run("./release_version.sh", cwd=new_checkout).stdout
    assert version in (
        "2021.8.20+095555.armenzg-semver.6517461",
        "2021.8.20+095555.HEAD.6517461",
    )
