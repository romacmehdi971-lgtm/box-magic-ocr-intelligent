#!/bin/bash
# deploy_mcp_cockpit_job.sh
# Déploiement MCP Cockpit IAPF en tant que Cloud Run Job PROD
# Mode one-shot : toutes les étapes dans un seul script

set -euo pipefail

# Configuration PROD
PROJECT_ID="box-magique-gp-prod"
REGION="us-central1"
JOB_NAME="mcp-cockpit-iapf-healthcheck"
SERVICE_ACCOUNT="mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}"
DOCKERFILE="mcp_cockpit/Dockerfile.job"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Vérifier le projet actif
log_info "Vérification du projet GCP actif..."
CURRENT_PROJECT=$(gcloud config get-value project)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    log_warn "Projet actuel: $CURRENT_PROJECT (attendu: $PROJECT_ID)"
    log_info "Configuration du projet $PROJECT_ID..."
    gcloud config set project "$PROJECT_ID"
fi

# 2. Activer les APIs nécessaires
log_info "Activation des APIs GCP..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    cloudscheduler.googleapis.com \
    --project="$PROJECT_ID" \
    --quiet

# 3. Vérifier que le service account existe
log_info "Vérification du service account..."
if gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" &>/dev/null; then
    log_info "Service account trouvé: $SERVICE_ACCOUNT"
else
    log_error "Service account $SERVICE_ACCOUNT n'existe pas!"
    log_info "Créez-le avec:"
    echo "gcloud iam service-accounts create mcp-cockpit --display-name='MCP Cockpit IAPF' --project=$PROJECT_ID"
    exit 1
fi

# 4. Build de l'image Docker
log_info "Build de l'image Docker..."
gcloud builds submit \
    --tag="$IMAGE_NAME" \
    --dockerfile="$DOCKERFILE" \
    --project="$PROJECT_ID" \
    --timeout=10m \
    .

if [ $? -ne 0 ]; then
    log_error "Échec du build Docker"
    exit 1
fi

log_info "Image Docker créée: $IMAGE_NAME"

# 5. Déployer le Cloud Run Job
log_info "Déploiement du Cloud Run Job..."
gcloud run jobs deploy "$JOB_NAME" \
    --image="$IMAGE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --service-account="$SERVICE_ACCOUNT" \
    --max-retries=1 \
    --task-timeout=10m \
    --memory=1Gi \
    --cpu=1 \
    --set-env-vars="ENVIRONMENT=PROD,USE_METADATA_AUTH=true" \
    --quiet

if [ $? -ne 0 ]; then
    log_error "Échec du déploiement du job"
    exit 1
fi

log_info "Job déployé avec succès: $JOB_NAME"

# 6. Afficher les commandes d'exécution
echo ""
log_info "=========================================="
log_info "DÉPLOIEMENT TERMINÉ"
log_info "=========================================="
echo ""
log_info "Commande pour exécuter le job (one-shot):"
echo "gcloud run jobs execute $JOB_NAME --region=$REGION --project=$PROJECT_ID"
echo ""
log_info "Commande pour voir les logs de la dernière exécution:"
echo "gcloud run jobs executions describe \$(gcloud run jobs executions list --job=$JOB_NAME --region=$REGION --limit=1 --format='value(name)') --region=$REGION"
echo ""
log_info "Commande pour créer une planification (ex: tous les jours à 6h UTC):"
echo "gcloud scheduler jobs create http ${JOB_NAME}-daily \\"
echo "  --location=$REGION \\"
echo "  --schedule='0 6 * * *' \\"
echo "  --uri='https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run' \\"
echo "  --http-method=POST \\"
echo "  --oauth-service-account-email=${SERVICE_ACCOUNT}"
echo ""
log_info "Documentation complète: docs/mcp/README.md"
