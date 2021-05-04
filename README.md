# Sentry Deploy Sync Hook

This repo contains a hook for updating the reference in getsentry to sentry automatically.

## Requirements

- Docker

## Pre-development

Create [a new SSH key](https://github.com/settings/keys) for this project, place the key in this repo as `private_ss_key`
(Git will ignore it) in order to get copied into the Docker image.

**NOTE**: It is super important you understand that this private key will be able to commit anywhere the associated user can.

Github webhook: TBD

## Development

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

If you want to actually commit code you will need to set the `DRY_RUN` env to False.

## Deployment

TBD

## Non-master Branches

If you want to have automatically updated references in getsentry for a non-master branch, do the following:

- Create a branch in "getsentry"
- Create a PR from the branch with **the same** name in "sentry" and add `#sync-getsentry` to the PR's description
