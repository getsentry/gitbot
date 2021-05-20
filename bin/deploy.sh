#!/bin/bash
# This script is only used for deploying a new version into the staging app
set -e

arg="$1"
if [ "$arg" != "production" ] && [ "$arg" != "staging" ]; then
	echo "You need to call this script with either production or staging"
	exit 1
fi

# GCR service name
SERVICE=sentry-deploy-sync-hook
if [ "$arg" == "staging" ]; then
	SERVICE="${SERVICE}-staging"
fi

gcloud run deploy "$SERVICE" \
	--image gcr.io/sentry-dev-tooling/sentry-deploy-sync-hook \
	--project=sentry-dev-tooling \
	--platform managed \
	--allow-unauthenticated \
	--region=us-central1

# TODO: Report the release
