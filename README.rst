Sentry Deploy Sync Hook
=======================

This repo contains a hook for updating the reference in getsentry to sentry automatically.

Requirements
------------
- Docker

Development
-----------

Copy the keys you want the service to use into the `key` directory which is ignored by Git.

Build image and run the project:

```shell
docker build -t getsentry/sync-hook .
docker run -i getsentry/sync-hook
```

If you want to access a container to tinker with:

```shell
docker run -it --rm getsentry/sync-hook bash
```

Non-master Branches
-------------------

If you want to have automatically updated references in getsentry for a non-master branch, do the following:

- Create a branch in "getsentry"
- Create a PR from the branch with **the same** name in "sentry" and add ``#sync-getsentry`` to the PR's description
