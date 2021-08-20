import time
from gitbot.lib import run

# XXX: Common logic move somewhere else
CHECKOUT_ROOT_PATH = __file__.rsplit("/", 2)[0]


def test_release_version(tmpdir):
    # XXX: This code needs to be turned into a fixture
    new_checkout = tmpdir
    run(f"git clone --depth 1 {CHECKOUT_ROOT_PATH} {new_checkout}")
    run("git checkout 5ba68307170688ab7ffbed696e4f61b8f6e767e7", cwd=new_checkout)
    version = run("./release_version.sh", cwd=CHECKOUT_ROOT_PATH).stdout
    # XXX: Adjust this code once it lands on master
    assert version == "2021.8.20+093132.armenzg/semver.5ba6830"
    # The release version should be idempotent
    time.sleep(3)
    version = run("./release_version.sh", cwd=CHECKOUT_ROOT_PATH).stdout
    assert version == "2021.8.20+093132.armenzg/semver.5ba6830"
