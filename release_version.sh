#!/bin/bash
# Script to generate a semver release version to be used by Sentry
# Known bugs:
# * date for the same timestamp is shifted across different OSes

# Using the commit timestamp as the source to generate release names ensures the idempotence of the process
COMMIT_TIMESTAMP=$(git show -s --format="%ct")
RELEASE=

if [[ $(uname -s) = 'Darwin' ]]; then
    COMMIT_SEMVER="$(date -r "${COMMIT_TIMESTAMP}" +'%Y.%m.%d+%H%M%S')"
else
    COMMIT_SEMVER="$(date -d @"${COMMIT_TIMESTAMP}" +'%Y.%m.%d+%H%M%S')"
fi
# Remove leading zeroes to make it valid semver
COMMIT_SEMVER=${COMMIT_SEMVER/.0/.}
BRANCH=$(git rev-parse --abbrev-ref HEAD)
# Remove backslahes since they are not permitted as valid releases
BRANCH=${BRANCH/\//-}
SHORT_SHA=$(git rev-parse --short HEAD)
# This is to help differentiate releases that are from code in master
if [ "${BRANCH}" != "master" ]; then
    RELEASE="${COMMIT_SEMVER}.${BRANCH}.${SHORT_SHA}"
else
    RELEASE="${COMMIT_SEMVER}.${SHORT_SHA}"
fi

echo "${RELEASE}"
