#!/bin/bash
# Script interactif pour push vers Container Registry et déploiement Cloud Run

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║     BOX MAGIC OCR - Container Registry & Cloud Run Setup     ║"
echo "║                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonctions utilitaires
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Vérifier si gcloud est installé
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI n'est pas installé."
    echo ""
    echo "Installation requise :"
    echo "  macOS   : brew install --cask google-cloud-sdk"
    echo "  Linux   : https://cloud.google.com/sdk/docs/install"
    echo "  Windows : https://cloud.google.com/sdk/docs/install"
    exit 1
fi

print_success "gcloud CLI détecté"

# Demander le Project ID
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Configuration du projet GCP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Afficher le projet actuel si configuré
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ -n "$CURRENT_PROJECT" ]; then
    print_info "Projet actuel : $CURRENT_PROJECT"
    echo ""
    read -p "Utiliser ce projet ? (o/n) [o] : " USE_CURRENT
    USE_CURRENT=${USE_CURRENT:-o}
    
    if [[ "$USE_CURRENT" =~ ^[Oo]$ ]]; then
        PROJECT_ID="$CURRENT_PROJECT"
    else
        read -p "Entrez votre Project ID GCP : " PROJECT_ID
    fi
else
    read -p "Entrez votre Project ID GCP : " PROJECT_ID
fi

# Vérifier que le projet existe
print_info "Vérification du projet $PROJECT_ID..."
if ! gcloud projects describe "$PROJECT_ID" &>/dev/null; then
    print_error "Le projet $PROJECT_ID n'existe pas ou vous n'y avez pas accès."
    exit 1
fi

print_success "Projet $PROJECT_ID validé"

# Configurer le projet
gcloud config set project "$PROJECT_ID" &>/dev/null

# Demander la région
echo ""
read -p "Région Cloud Run [europe-west1] : " REGION
REGION=${REGION:-europe-west1}

# Demander le nom du service
echo ""
read -p "Nom du service [box-magic-ocr-intelligent] : " SERVICE_NAME
SERVICE_NAME=${SERVICE_NAME:-box-magic-ocr-intelligent}

# Image name
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Résumé de la configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Project ID      : $PROJECT_ID"
echo "  Région          : $REGION"
echo "  Service         : $SERVICE_NAME"
echo "  Image           : $IMAGE_NAME:latest"
echo ""
read -p "Continuer avec cette configuration ? (o/n) [o] : " CONFIRM
CONFIRM=${CONFIRM:-o}

if [[ ! "$CONFIRM" =~ ^[Oo]$ ]]; then
    echo "Annulé par l'utilisateur."
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Étape 1 : Activation des APIs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

print_info "Activation de Cloud Build API..."
gcloud services enable cloudbuild.googleapis.com --project="$PROJECT_ID" &>/dev/null
print_success "Cloud Build API activée"

print_info "Activation de Container Registry API..."
gcloud services enable containerregistry.googleapis.com --project="$PROJECT_ID" &>/dev/null
print_success "Container Registry API activée"

print_info "Activation de Cloud Run API..."
gcloud services enable run.googleapis.com --project="$PROJECT_ID" &>/dev/null
print_success "Cloud Run API activée"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Étape 2 : Build & Push de l'image Docker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

print_info "Build de l'image avec Google Cloud Build..."
echo ""
echo "Cela peut prendre 5-10 minutes..."
echo ""

if gcloud builds submit --tag "$IMAGE_NAME:latest" . --project="$PROJECT_ID"; then
    print_success "Image buildée et pushée avec succès !"
    echo ""
    print_info "Image disponible : $IMAGE_NAME:latest"
else
    print_error "Échec du build"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Étape 3 : Vérification de l'image"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

print_info "Liste des images dans GCR..."
gcloud container images list-tags "$IMAGE_NAME" --project="$PROJECT_ID"
echo ""

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Étape 4 : Déploiement sur Cloud Run"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Déployer sur Cloud Run maintenant ? (o/n) [o] : " DEPLOY
DEPLOY=${DEPLOY:-o}

if [[ "$DEPLOY" =~ ^[Oo]$ ]]; then
    print_info "Déploiement sur Cloud Run..."
    echo ""
    
    if gcloud run deploy "$SERVICE_NAME" \
        --image "$IMAGE_NAME:latest" \
        --platform managed \
        --region "$REGION" \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 1 \
        --timeout 300 \
        --max-instances 10 \
        --set-env-vars "ENABLE_RUNTIME_DIAGNOSTICS=true" \
        --project="$PROJECT_ID"; then
        
        print_success "Déploiement réussi !"
        echo ""
        
        # Récupérer l'URL
        SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
            --region "$REGION" \
            --project="$PROJECT_ID" \
            --format 'value(status.url)')
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  🎉 Déploiement terminé avec succès !"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "  Service URL : $SERVICE_URL"
        echo ""
        echo "  Endpoints disponibles :"
        echo "    • Health check  : $SERVICE_URL/health"
        echo "    • Root info     : $SERVICE_URL/"
        echo "    • OCR endpoint  : $SERVICE_URL/ocr (POST)"
        echo ""
        echo "  Test rapide :"
        echo "    curl $SERVICE_URL/health"
        echo ""
        
        # Tester le health check
        print_info "Test du health check..."
        sleep 3
        if curl -s "$SERVICE_URL/health" | grep -q "healthy"; then
            print_success "Service opérationnel !"
        else
            print_error "Le service ne répond pas correctement"
        fi
        
    else
        print_error "Échec du déploiement"
        exit 1
    fi
else
    print_info "Déploiement ignoré. Vous pouvez déployer plus tard avec :"
    echo ""
    echo "  gcloud run deploy $SERVICE_NAME \\"
    echo "    --image $IMAGE_NAME:latest \\"
    echo "    --platform managed \\"
    echo "    --region $REGION \\"
    echo "    --memory 2Gi \\"
    echo "    --allow-unauthenticated"
    echo ""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Commandes utiles"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  # Voir les logs du service"
echo "  gcloud run services logs read $SERVICE_NAME --region $REGION"
echo ""
echo "  # Lister les images"
echo "  gcloud container images list-tags $IMAGE_NAME"
echo ""
echo "  # Mettre à jour le service"
echo "  gcloud run services update $SERVICE_NAME \\"
echo "    --image $IMAGE_NAME:TAG --region $REGION"
echo ""

print_success "Script terminé !"
