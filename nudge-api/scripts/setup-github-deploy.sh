#!/usr/bin/env bash
# One-time setup so GitHub Actions can deploy the API (.github/workflows/deploy.yml).
# Run it yourself, signed in to gcloud as a project owner:
#
#     bash nudge-api/scripts/setup-github-deploy.sh
#
# It creates:
# - a "github-deployer" service account with only the roles a Cloud Run source
#   deploy needs (it can't read secrets or the database);
# - a Workload Identity Federation pool and provider that accept GitHub's sign-in
#   only from pushes to main of biplopghimire/Nudge. No keys are created or stored.
# Safe to run again: anything that already exists is kept.
set -uo pipefail

PROJECT=nudge-513020
PROJECT_NUMBER=214919077406
REPO_ID=1411061976 # biplopghimire/Nudge (a rename or transfer keeps this id)
SA="github-deployer@$PROJECT.iam.gserviceaccount.com"
POOL=github
PROVIDER=nudge-repo

step() { echo; echo "== $*"; }

step "Enable the token exchange API"
gcloud services enable sts.googleapis.com iamcredentials.googleapis.com --project "$PROJECT"

step "Service account $SA"
gcloud iam service-accounts describe "$SA" --project "$PROJECT" >/dev/null 2>&1 \
  || gcloud iam service-accounts create github-deployer --project "$PROJECT" \
       --display-name "GitHub Actions deployer (biplopghimire/Nudge main)"

step "Roles for deploying from source"
for role in roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.writer \
            roles/storage.admin roles/serviceusage.serviceUsageConsumer roles/logging.viewer; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$SA" --role "$role" \
    --condition=None --quiet >/dev/null && echo "   $role"
done

step "Let it start builds and run the API as the existing service accounts"
for runas in "nudge-backend@$PROJECT.iam.gserviceaccount.com" "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"; do
  gcloud iam service-accounts add-iam-policy-binding "$runas" --project "$PROJECT" \
    --member "serviceAccount:$SA" --role roles/iam.serviceAccountUser --quiet >/dev/null && echo "   $runas"
done

step "Workload Identity pool and GitHub provider"
gcloud iam workload-identity-pools describe "$POOL" --project "$PROJECT" --location global >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools create "$POOL" --project "$PROJECT" --location global \
       --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers describe "$PROVIDER" --project "$PROJECT" --location global \
    --workload-identity-pool "$POOL" >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --project "$PROJECT" --location global \
       --workload-identity-pool "$POOL" --display-name "biplopghimire/Nudge" \
       --issuer-uri "https://token.actions.githubusercontent.com" \
       --attribute-mapping "google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.ref=assertion.ref" \
       --attribute-condition "assertion.repository_id == '$REPO_ID' && assertion.ref == 'refs/heads/main'"

step "Let the repository's main branch use the service account"
gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$PROJECT" --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/attribute.repository_id/$REPO_ID" \
  --quiet >/dev/null && echo "   done"

echo
echo "Done. Merges to main that change nudge-api/ now deploy automatically."
