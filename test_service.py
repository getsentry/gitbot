import requests

# url = "https://sentry-deploy-sync-hook-dwunkkvj6a-uc.a.run.app"
url = "http://0.0.0.0:8080"
myobj = {"somekey": "somevalue"}

x = requests.post(url, data=myobj)

print(x.text)
