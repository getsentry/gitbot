name=sentry-deploy-sync-hook
project=todo  # TODO: dev-productivity project?

build () {
    gcloud --project internal-sentry \
    builds submit --tag "us.gcr.io/${project}/${name}"
}

deploy () {
  # --max-instances=2
  #   99% of scenarios should be handled easily by 1 instance.
  # --memory=256Mi
  #   This should be sufficient for an instance, read the Dockerfile.
  # --cpu=1000m
  #   This is the minimum allowed setting.

	gcloud --project "$project" run deploy "$name" \
			--image "us.gcr.io/${project}/${name}:latest" \
			--platform=managed \
			--allow-unauthenticated \
			--region=us-central1 \
			--port=8080 \
			--cpu=1000m \
			--memory=256Mi \
			--timeout=10m \
			--min-instances=1 \
			--max-instances=2
}

set -x
build
deploy
