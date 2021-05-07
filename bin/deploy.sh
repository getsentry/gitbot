#!/bin/bash
set -e
# It matches the Docker image name
NAME=sentry-deploy-sync-hook
# It matches the GCR project
PROJECT=sentry-dev-tooling
# It matches the service name in GCR
SERVICE=$NAME-$ENVIRONMENT
IMAGE=gcr.io/${PROJECT}/${NAME}

# Require the
while getopts e: flag; do
	case "${flag}" in
	e) ENVIRONMENT=${OPTARG} ;;
	*)
		echo 'Error in command line parsing' >&2
		exit 1
		;;
	esac
done
: ${ENVIRONMENT:?Set the environment with -e}
env_vars="ENVIRONMENT=${ENVIRONMENT},"

set -x
# XXX: When running deploy.sh for production we need to make sure that we don't publish
# a new image since we've already built one for staging
exit 1
gcloud builds submit --tag $IMAGE --project=$PROJECT
gcloud run deploy $SERVICE \
	--image $IMAGE \
	--set-env-vars="$env_vars" \
	--project=$PROJECT \
	--platform managed \
	--allow-unauthenticated \
	--add-cloudsql-instances ${DB_INSTANCE_CONNECTION_NAME} \
	--region=us-west1
