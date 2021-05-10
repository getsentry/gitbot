#!/bin/bash
# This script is only used for deploying a new version into the staging app
set -e

NAME=sentry-deploy-sync-hook # It matches the Docker image name
PROJECT=sentry-dev-tooling   # It matches the GCR project
IMAGE=gcr.io/${PROJECT}/${NAME}

SERVICE=sentry-deploy-sync-hook # GCR service name

# The image needs to be build prior to executing this step
gcloud builds submit --tag $IMAGE --project=$PROJECT
gcloud run deploy "$SERVICE" \
	--image $IMAGE \
	--project=$PROJECT \
	--platform managed \
	--allow-unauthenticated \
	--region=us-west1
