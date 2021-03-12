Sentry Deploy Sync Hook
=======================

This repo contains a hook for updating the reference in getsentry
to sentry automatically.

Logging: TODO link to stackdriver
Sentry Project : TODO

Deployment
----------

TODO


Non-master Branches
-------------------

If you want to have automatically updated references in getsentry for a non-master branch, do the following:

- Create a branch in "getsentry"
- Create a PR from the branch with **the same** name in "sentry" and add ``#sync-getsentry`` to the PR's description
