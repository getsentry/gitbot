import os
import requests

# url = "https://sentry-deploy-sync-hook-dwunkkvj6a-uc.a.run.app"
url = "http://0.0.0.0:5000"
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")

events = [
    (
        {
            "ref": "refs/heads/master",
            "repository": {"full_name": "getsentry/sentry"},
            "head_commit": {
                "id": "438cb62a559889b5ae68ce3494c1034c60e50f4a",
                "author": {"name": "wmak", "email": "william@wmak.io"},
            },
        },
        {
            "X-Hub-Signature": GITHUB_WEBHOOK_SECRET,
            "X-GitHub-Event": "push",
        },
    ),
]

for body, header in events:
    x = requests.post(url, headers=header, json=body)
    print(x.text)
