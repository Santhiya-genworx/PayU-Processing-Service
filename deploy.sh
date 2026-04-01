#!/bin/bash

# === Project / Service Settings ===
PROJECT_ID="gwx-internship-01"
REGION="us-east1"

SERVICE_NAME="payu-processing-service"
GAR_REPO="us-east1-docker.pkg.dev/$PROJECT_ID/gwx-gar-intern-01"

IMAGE="$GAR_REPO/payu-processing-service:latest"
WORKER_IMAGE="$GAR_REPO/payu-worker:latest"

# === Database Settings ===
DB_USER="santhiyas"
DB_PASS="D5#0GFh0LLenU2pqfc7"
DB_NAME="payu"
DB_HOST="34.23.138.181"
DB_PORT=5432
CONN_NAME="gwx-internship-01:us-east1:gwx-csql-intern-01"
DB_URL="postgresql+asyncpg://$DB_USER:$DB_PASS@/$DB_NAME?host=/cloudsql/$CONN_NAME"

# === Redis Settings ===
REDIS_HOST="10.125.46.155"
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL="redis://$REDIS_HOST:$REDIS_PORT/$REDIS_DB"

ORIGINS=https://payu-frontend-717740758627.us-east1.run.app

# === Shared env vars ===
SHARED_ENV="DB_URL=$DB_URL,DB_HOST=$DB_HOST,DB_USER=$DB_USER,DB_PASSWORD=$DB_PASS,DB_NAME=$DB_NAME,DB_PORT=$DB_PORT,REDIS_HOST=$REDIS_HOST,REDIS_PORT=$REDIS_PORT,REDIS_DB=$REDIS_DB,REDIS_URL=$REDIS_URL,PYTHONUNBUFFERED=1,ORIGINS=$ORIGINS"

# === Build Once, Tag Twice ===
echo "Building image..."
docker build -t $IMAGE .
docker tag $IMAGE $WORKER_IMAGE

echo "Pushing images..."
docker push $IMAGE
docker push $WORKER_IMAGE

# === Deploy API ===
echo "Deploying API..."
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE \
  --region=$REGION \
  --allow-unauthenticated \
  --project=$PROJECT_ID \
  --platform=managed \
  --port=8002 \
  --max-instances=2 \
  --min-instances=1 \
  --min=0 \
  --max=2 \
  --service-account=gwx-cloudrun-sa-01@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances=$CONN_NAME \
  --set-env-vars="$SHARED_ENV" \
  --network=gwx-vpc-intern-01 \
  --subnet=gwx-sne-intern-01 \
  --vpc-egress=private-ranges-only

# === Deploy Worker ===
# echo "Deploying Worker..."
# gcloud run deploy payu-worker \
#   --image=$WORKER_IMAGE \
#   --region=$REGION \
#   --project=$PROJECT_ID \
#   --platform=managed \
#   --allow-unauthenticated \
#   --service-account=gwx-cloudrun-sa-01@$PROJECT_ID.iam.gserviceaccount.com \
#   --min-instances=1 \
#   --max-instances=1 \
#   --min=1 \
#   --max=1 \
#   --add-cloudsql-instances=$CONN_NAME \
#   --set-env-vars="$SHARED_ENV" \
#   --network=gwx-vpc-intern-01 \
#   --subnet=gwx-sne-intern-01 \
#   --vpc-egress=private-ranges-only \
#   --command="sh" \
#   --args="-c,python -m http.server 8002 & python -m src.utils.worker" \
#   --no-deploy-health-check

echo "Deployment completed!"