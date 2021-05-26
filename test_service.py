import hashlib
import hmac
import json
import os
import requests

# Staging
# url = "https://sentry-deploy-sync-hook-dwunkkvj6a-uc.a.run.app"
# Production
# url = TBD
# Development
url = "http://0.0.0.0:5000"

GITHUB_WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]

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
            "X-GitHub-Event": "push",
            "Content-Type": "application/json",
        },
    ),
]

for body, header in events:
    new_body = json.dumps(body).encode("utf-8")
    signature = hmac.new(
        GITHUB_WEBHOOK_SECRET.encode("utf-8"), new_body, hashlib.sha1
    ).hexdigest()
    header["X-Hub-Signature"] = f"sha1={signature}"
    x = requests.post(url, headers=header, data=new_body)
    print(x.text)
