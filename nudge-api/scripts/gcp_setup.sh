#!/usr/bin/env bash
# One-time Google Cloud permissions for Nudge (Sprint 3 plan, Part 2).
# Run it yourself, signed in with `gcloud auth login` as the project owner:
#
#     bash scripts/gcp_setup.sh
#
# Safe to run again. The bucket itself was created with:
#     gcloud storage buckets create gs://nudge-course-files --location us-east1 \
#         --default-storage-class STANDARD --uniform-bucket-level-access --public-access-prevention
set -euo pipefail

PROJECT=nudge-513020
BUCKET=gs://nudge-course-files
SA_NAME=nudge-backend
SA="$SA_NAME@$PROJECT.iam.gserviceaccount.com"
ME="$(gcloud config get-value account 2>/dev/null)"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
BUILD_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

echo "1/5 Service account $SA"
gcloud iam service-accounts describe "$SA" --project "$PROJECT" >/dev/null 2>&1 ||
  gcloud iam service-accounts create "$SA_NAME" --project "$PROJECT" --display-name "Nudge backend"

# A new service account takes a little while to be visible to other services.
retry() {
  for attempt in 1 2 3 4 5 6; do
    "$@" && return 0
    echo "   not ready yet, retrying in 10s ($attempt/6)"
    sleep 10
  done
  return 1
}

echo "2/5 The backend can read and write the bucket (and nothing else in Cloud Storage)"
retry gcloud storage buckets add-iam-policy-binding "$BUCKET" \
  --member "serviceAccount:$SA" --role roles/storage.objectAdmin --format none

echo "3/5 The backend can sign 15-minute file links as itself (no key file)"
retry gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$PROJECT" \
  --member "serviceAccount:$SA" --role roles/iam.serviceAccountTokenCreator --format none

echo "4/5 You ($ME) can act as the backend locally, so your laptop uses the same access"
retry gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$PROJECT" \
  --member "user:$ME" --role roles/iam.serviceAccountTokenCreator --format none

echo "5/5 The backend can read its secrets; Cloud Build can build the container"
retry gcloud projects add-iam-policy-binding "$PROJECT" \
  --member "serviceAccount:$SA" --role roles/secretmanager.secretAccessor --condition None --format none
retry gcloud projects add-iam-policy-binding "$PROJECT" \
  --member "serviceAccount:$BUILD_SA" --role roles/run.builder --condition None --format none

echo "Done. Permissions can take a minute to apply."
