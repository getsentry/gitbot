from gitbot.models import RepoUrl


def test_redacted_repo_url_with_pat():
    pat = "NotAnActualPAT1234"
    repo_url = RepoUrl(repo="getsentry/random-repo", user="username", pat=pat)

    expected_str = "https://username:**REDACTED**@github.com/getsentry/random-repo"

    assert expected_str == f"{repo_url}"
    assert pat not in f"{repo_url}"


def test_repo_url_secret_value():
    pat = "NotAnActualPAT1234"
    repo_url = RepoUrl(repo="getsentry/random-repo", user="username", pat=pat)

    expected_str = (
        "https://username:NotAnActualPAT1234@github.com/getsentry/random-repo"
    )

    assert expected_str == f"{repo_url.get_secret_value()}"


def test_repo_url_eq():
    repo_url_2 = RepoUrl(
        repo="getsentry/random-repo", user="username", pat="NotAnActualPAT1234"
    )
    repo_url_1 = RepoUrl(
        repo="getsentry/random-repo", user="username", pat="NotAnActualPAT1234"
    )

    assert repo_url_1 == repo_url_2


def test_repo_url_not_eq():
    repo_url_2 = RepoUrl(
        repo="getsentry/random-repo-1", user="username", pat="NotAnActualPAT1234"
    )

    repo_url_1 = RepoUrl(
        repo="getsentry/random-repo", user="username", pat="NotAnActualPAT1234"
    )

    assert repo_url_1 != repo_url_2
