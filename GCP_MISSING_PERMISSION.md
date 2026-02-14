# 🚨 PERMISSION GCP MANQUANTE

**Date** : 2026-02-14 20:48:00  
**Erreur** : `PERMISSION_DENIED: Permission 'artifactregistry.repositories.downloadArtifacts' denied`

---

## 🔧 SOLUTION IMMÉDIATE

Le compte de service `genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com` a besoin du rôle **Artifact Registry Reader** pour télécharger les images Docker depuis GCR/Artifact Registry.

### Commande à exécuter dans Cloud Shell :

```bash
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```

### OU via la Console Web GCP :

1. Ouvrez : https://console.cloud.google.com/iam-admin/iam?project=box-magique-gp-prod
2. Trouvez le compte de service : `genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com`
3. Cliquez sur **✏️ Modifier**
4. Cliquez sur **+ AJOUTER UN AUTRE RÔLE**
5. Ajoutez le rôle : **`Artifact Registry Reader`** (`roles/artifactregistry.reader`)
6. Cliquez sur **ENREGISTRER**

---

## 📋 RÉCAPITULATIF DES RÔLES REQUIS

Pour un déploiement Cloud Run complet, le compte de service doit avoir :

1. ✅ **Cloud Run Admin** (`roles/run.admin`) - AJOUTÉ
2. ✅ **Cloud Build Editor** (`roles/cloudbuild.builds.editor`) - AJOUTÉ
3. ✅ **Service Account User** (`roles/iam.serviceAccountUser`) - AJOUTÉ
4. ✅ **Storage Admin** (`roles/storage.admin`) - AJOUTÉ
5. ❌ **Artifact Registry Reader** (`roles/artifactregistry.reader`) - **MANQUANT**

---

## ⏱️ TEMPS D'ACTIVATION

**Propagation des permissions** : 1-3 minutes après l'ajout du rôle.

---

## ✅ CE QUI A FONCTIONNÉ

- ✅ Build Docker réussi (build ID : `eabc3de5-d0ec-40f3-85f8-d03f0b868516`)
- ✅ Image poussée vers : `gcr.io/box-magique-gp-prod/box-magic-ocr-intelligent:0ba4a18`
- ✅ Cloud Run service `box-magic-ocr-intelligent` existe déjà
- ⏸️ Déploiement de la nouvelle révision bloqué (permission manquante)

---

## 🔄 PROCHAINE ÉTAPE

Après l'ajout du rôle `Artifact Registry Reader`, je pourrai immédiatement :

1. Relancer le déploiement Cloud Run
2. Vérifier la nouvelle révision
3. Tester le healthcheck
4. Valider les Apps Script
5. Exécuter les tests finaux

---

**Informations de déploiement** :
- **Branche** : `main`
- **Commit** : `0ba4a18f596f00e5fd01d08f27a7a6fb9db49cf6`
- **Version** : `1.0.1`
- **Image Docker** : `gcr.io/box-magique-gp-prod/box-magic-ocr-intelligent:0ba4a18`
- **Build Status** : ✅ SUCCESS
- **Deployment Status** : ⏸️ EN ATTENTE (permission manquante)

---

**Une fois le rôle ajouté, répondez simplement "OK" et je finaliserai automatiquement.**
