# Sentry Deploy Sync Hook

This repo contains a hook for updating the reference in getsentry to sentry automatically.

## Requirements

- Docker

## Development

Create [a new SSH key](https://github.com/settings/keys) for this project, place the key in this repo as `private_ss_key`
(Git will ignore it) in order to get copied into the Docker image.

**NOTE**: It is super important you understand that this private key will be able to commit anywhere the associated Github user can. It is encouraged you delete the private key from Github as soon as you're done.

Github webhook: TBD

We use docker compose to help with live code reloading (since we mount a volume to the source checkout):

```shell
docker compose up --build
```

To test the API you can use `curl`:

```shell
curl \
    --header "Content-Type: application/json" \
    --header 'X-GitHub-Event: push' \
    --request POST \
    --data '{"ref":"refs/heads/master","repository":{"full_name":"getsentry/sentry"},"head_commit":{"id":"438cb62a559889b5ae68ce3494c1034c60e50f4a","author":{"name":"wmak","email":"william@wmak.io"}}}' \
    http://0.0.0.0:5000
```

### Running the pipeline locally

**NOTE**: The development set up will not commit code unless you set `DRY_RUN` env to False.

**NOTE**: We assume you have the backend running on your localhost (see steps on section above).

**NOTE**: By default, the development set up will push changes to [sentry-deploy-sync-hook-test-repo](https://github.com/getsentry/sentry-deploy-sync-hook-test-repo). To test against another repo you can use the env variable `DEPLOY_REPO` in order to point to a different repo you have write access to. In order for this to work, such repo needs `bin/bump-sentry` and `cloudbuild.yaml` from the getsentry repo.

In order to test Github changes through your local set up you need to follow these steps:

- Run `docker compose up --build -e DRY_RUN=False`
  - Verify the output says dry run mode to be off and which repo it will push to
- Set up [Ngrok](https://ngrok.io/) to redirect Github calls to your localhost
  - `ngrok http 5000` --> Grab the URL ngrok gives you (e.g. `https://6a88fe29c5cc.ngrok.io`)
- Fork sentry and create a webhook under the repo's settings
  - Point it to the URL that ngrok gives you
  - Choose `application/json` for `Content type`
  - For a production set-up you will want to define a [Secret](https://docs.github.com/en/developers/webhooks-and-events/creating-webhooks#secret)
    - TODO: Verify we have code that checks `X-Hub-Signature` and `X-Hub-Signature-256`
  - Create a branch named `test-branch` and make sure you set the upstream to your fork
  - From here on, pushes to that branch (or `master`) will be processed by the backend
  - You can use this command: `echo "$(date)" > file && git add file && git commit -m "Foo" --no-verify && git push`

## Deployment

TBD

## Non-master Branches

If you want to have automatically updated references in getsentry for a non-master branch, do the following:

- Create a branch in "getsentry"
- Create a PR from the branch with **the same** name in "sentry" and add `#sync-getsentry` to the PR's description
