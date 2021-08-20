import time
from gitbot.lib import run

# XXX: Common logic move somewhere else
CHECKOUT_ROOT_PATH = __file__.rsplit("/", 2)[0]


def test_release_version(tmpdir):
    # XXX: This code needs to be turned into a fixture
    new_checkout = tmpdir
    # We clone deeper than 1 since we need to checkout an old revision
    run(f"git clone --depth 10 {CHECKOUT_ROOT_PATH} {new_checkout}")
    run("git log -5 --oneline", cwd=new_checkout)
    run("git checkout 68fd0d2aa1dbdc72af79b85f7d65a81fb4723dbd", cwd=new_checkout)
    version = run("./release_version.sh", cwd=new_checkout).stdout
    # XXX: Adjust the version once it lands on master
    assert version in (
        "2021.8.20+102918.armenzg-semver.68fd0d2",
        "2021.8.20+102918.HEAD.68fd0d2",
    )
    # The release version should be idempotent
    time.sleep(3)
    version = run("./release_version.sh", cwd=new_checkout).stdout
    assert version in (
        "2021.8.20+102918.armenzg-semver.68fd0d2",
        "2021.8.20+102918.HEAD.68fd0d2",
    )
