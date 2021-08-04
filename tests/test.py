# Generic name since the names of the source code is needs some refactoring first
from deployhook import extract_author

event = {
    "after": "40b0be642943c36cf602c5bd072fdc937ba7d687",
    "before": "05ae9441b0974195bdc80144ab6b9f9d5cd97796",
    "created": False,
    "deleted": False,
    "forced": False,
    "organization": {
        "events_url": "https://api.github.com/orgs/getsentry/events",
        "hooks_url": "https://api.github.com/orgs/getsentry/hooks",
        "id": 1396951,
        "issues_url": "https://api.github.com/orgs/getsentry/issues",
        "login": "getsentry",
        "members_url": "https://api.github.com/orgs/getsentry/members{/member}",
        "node_id": "MDEyOk9yZ2FuaXphdGlvbjEzOTY5NTE=",
        "public_members_url": "https://api.github.com/orgs/getsentry/public_members{/member}",
        "repos_url": "https://api.github.com/orgs/getsentry/repos",
        "url": "https://api.github.com/orgs/getsentry",
    },
    "pusher": {
        "email": "85517732+AniketDas-Tekky@users.noreply.github.com",
        "name": "AniketDas-Tekky",
    },
    "ref": "refs/heads/master",
    "repository": {
        "description": "Sentry is cross-platform application monitoring, with a focus on error reporting.",
        "fork": False,
        "full_name": "getsentry/sentry",
        "html_url": "https://github.com/getsentry/sentry",
        "id": 873328,
        "name": "sentry",
        "node_id": "MDEwOlJlcG9zaXRvcnk4NzMzMjg=",
        "owner": {
            "avatar_url": "https://avatars.githubusercontent.com/u/1396951?v=4",
            "email": None,
            "followers_url": "https://api.github.com/users/getsentry/followers",
            "gravatar_id": "",
            "html_url": "https://github.com/getsentry",
            "id": 1396951,
            "login": "getsentry",
            "name": "getsentry",
            "node_id": "MDEyOk9yZ2FuaXphdGlvbjEzOTY5NTE=",
            "url": "https://api.github.com/users/getsentry",
        },
        "private": False,
        "url": "https://github.com/getsentry/sentry",
    },
    "sender": {
        "avatar_url": "https://avatars.githubusercontent.com/u/85517732?v=4",
        "followers_url": "https://api.github.com/users/AniketDas-Tekky/followers",
        "following_url": "https://api.github.com/users/AniketDas-Tekky/following{/other_user}",
        "gists_url": "https://api.github.com/users/AniketDas-Tekky/gists{/gist_id}",
        "gravatar_id": "",
        "html_url": "https://github.com/AniketDas-Tekky",
        "id": 85517732,
        "login": "AniketDas-Tekky",
        "node_id": "MDQ6VXNlcjg1NTE3NzMy",
        "url": "https://api.github.com/users/AniketDas-Tekky",
    },
}


def test_extract_author():
    author = extract_author({"author": "foo"})
    assert author == ""
