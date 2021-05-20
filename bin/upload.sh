#!/bin/bash
# This script is only used for deploying a new version into the staging app
set -e

NAME=sentry-deploy-sync-hook
PROJECT=sentry-dev-tooling
IMAGE=gcr.io/${PROJECT}/${NAME}

docker build --tag ${NAME}:latest .
docker tag ${NAME} ${IMAGE}
docker push ${IMAGE}
