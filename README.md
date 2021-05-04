# Sentry Deploy Sync Hook

This repo contains a hook for updating the reference in getsentry to sentry automatically.

## Requirements

- Docker

## Pre-development

Create [a new SSH key](https://github.com/settings/keys) for this project, place the key in this repo as `private_ss_key`
(Git will ignore it) in order to get copied into the Docker image.

Github webhook: TBD

## Development

We use docker compose to help with live code reloading:

```shell
docker compose up --build
```

If you want to access a container to tinker with it:

```shell
docker compose run backend bash
```

## Deployment

TBD

## Non-master Branches

If you want to have automatically updated references in getsentry for a non-master branch, do the following:

- Create a branch in "getsentry"
- Create a PR from the branch with **the same** name in "sentry" and add `#sync-getsentry` to the PR's description
