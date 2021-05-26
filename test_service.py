import os
import requests

# url = "https://sentry-deploy-sync-hook-dwunkkvj6a-uc.a.run.app"
url = "http://0.0.0.0:8080"
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")
myobj = {
    "somekey": "somevalue",
}
headers = {
    "X-Hub-Signature": GITHUB_WEBHOOK_SECRET,
}

x = requests.post(url, headers=headers, data=myobj)

print(x.text)
