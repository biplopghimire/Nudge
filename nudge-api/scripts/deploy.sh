#!/usr/bin/env bash
# Deploy the Nudge API to Cloud Run (Sprint 3 plan, Part 1). Run it yourself:
#
#     bash nudge-api/scripts/deploy.sh
#
# The first run stores three secrets in Secret Manager (read from nudge-api/.env,
# never printed): the Supabase URL, the Gemini key and a new login-token secret.
# Later runs reuse them and only redeploy the code. To change a secret:
#     printf '%s' "new value" | gcloud secrets versions add nudge-gemini-api-key --data-file=-
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT=nudge-513020
REGION=us-east1
SERVICE=nudge-api
SA="nudge-backend@$PROJECT.iam.gserviceaccount.com"

env_value() { grep "^$1=" .env | head -1 | cut -d= -f2- | tr -d '\n'; }

create_secret() { # name; value on stdin
  if gcloud secrets describe "$1" --project "$PROJECT" >/dev/null 2>&1; then
    cat >/dev/null
    echo "   $1 already exists (kept)"
  else
    gcloud secrets create "$1" --project "$PROJECT" --replication-policy automatic --data-file=- >/dev/null
    echo "   created $1"
  fi
}

DATABASE_URL="$(env_value NUDGE_PROD_DATABASE_URL)"
GEMINI_KEY="$(env_value NUDGE_GEMINI_API_KEY)"
if [[ -z "$DATABASE_URL" || "$DATABASE_URL" == *"[YOUR-PASSWORD]"* ]]; then
  echo "Set NUDGE_PROD_DATABASE_URL in nudge-api/.env first."; exit 1
fi
[[ -n "$GEMINI_KEY" ]] || { echo "Set NUDGE_GEMINI_API_KEY in nudge-api/.env first."; exit 1; }

echo "1/2 Secrets"
printf '%s' "$DATABASE_URL" | create_secret nudge-database-url
printf '%s' "$GEMINI_KEY" | create_secret nudge-gemini-api-key
python3 -c "import secrets, sys; sys.stdout.write(secrets.token_urlsafe(48))" | create_secret nudge-jwt-secret

echo "2/2 Build and deploy (takes a few minutes the first time)"
# --no-cpu-throttling keeps upload processing (a background task) running after
#   the upload request returns.
# --allow-unauthenticated lets the app reach the API; the API checks its own login tokens.
gcloud run deploy "$SERVICE" \
  --project "$PROJECT" --region "$REGION" --source . --quiet \
  --service-account "$SA" \
  --allow-unauthenticated \
  --no-cpu-throttling --cpu 1 --memory 1Gi --timeout 300 \
  --min-instances 0 --max-instances 2 \
  --set-env-vars "NUDGE_REPOSITORY=postgres,NUDGE_AI=gemini,NUDGE_STORAGE=gcs,NUDGE_AUTH=jwt" \
  --set-secrets "NUDGE_DATABASE_URL=nudge-database-url:latest,NUDGE_GEMINI_API_KEY=nudge-gemini-api-key:latest,NUDGE_JWT_SECRET=nudge-jwt-secret:latest"

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format 'value(status.url)')"
echo
echo "Deployed: $URL"
echo "Docs:     $URL/docs"
curl -s "$URL/health" && echo
