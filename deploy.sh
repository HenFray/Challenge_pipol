#!/bin/bash

# Salir inmediatamente si un comando falla
set -e

# --- Cargar Configuración desde config/config_deploy.env ---
CONFIG_FILE="config/config_deploy.env"

if [ -f "$CONFIG_FILE" ]; then
    echo "Cargando configuración desde $CONFIG_FILE..."
    set -a
    source "$CONFIG_FILE"
    set +a
    echo "Configuración cargada."
else
    echo "Error: Archivo de configuración '$CONFIG_FILE' no encontrado. Saliendo."
    exit 1
fi

# --- Validar Parámetros Críticos ---
# Ahora usamos los nombres de variable del archivo .env, por ejemplo, GCP_PROJECT_ID
if [ -z "$GCP_PROJECT_ID" ]; then
  echo "Error: 'GCP_PROJECT_ID' no está definido o está vacío en $CONFIG_FILE. Saliendo."
  exit 1
fi


if [[ "$GCP_PROJECT_ID" == "TU_PROJECT_ID_DE_GCP" ]] || \
   ([[ -n "$SERVICE_ACCOUNT" ]] && [[ "$SERVICE_ACCOUNT" == TU_CUENTA_SERVICIO* ]]); then
 echo "Advertencia: Aún parece haber valores placeholder ('TU_...') en $CONFIG_FILE."
 echo "Por favor, actualiza $CONFIG_FILE con tus valores reales antes de ejecutar."
 echo "Saliendo para evitar errores."
 exit 1
fi


echo "Configuración a usar:"
echo "  PROJECT_ID: $GCP_PROJECT_ID"
echo "  REGION: $GCP_REGION"
echo "  SERVICE_ACCOUNT: ${SERVICE_ACCOUNT:-[Usando Default]}" # Muestra '[Usando Default]' si SERVICE_ACCOUNT está vacío
echo "  ARTIFACT_REPO: $ARTIFACT_REPO_NAME"
echo "  IMAGE_NAME: $IMAGE_NAME"
echo "  JOB_NAME: $JOB_NAME"
echo "  JOB_MEMORY: $JOB_MEMORY"
echo "  JOB_CPU: $JOB_CPU"
echo "  JOB_TIMEOUT: $JOB_TIMEOUT"


# Configurar gcloud para usar tu proyecto
echo "Configurando gcloud para usar el proyecto: ${GCP_PROJECT_ID}"
gcloud config set project ${GCP_PROJECT_ID}

# Habilitar APIs necesarias
echo "Habilitando APIs necesarias (Cloud Build, Artifact Registry, Cloud Run)..."
gcloud services enable \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  iam.googleapis.com

# Crear el repositorio en Artifact Registry si no existe
echo "Verificando/Creando repositorio en Artifact Registry: ${ARTIFACT_REPO_NAME}"
gcloud artifacts repositories describe ${ARTIFACT_REPO_NAME} --location=${GCP_REGION} --project=${GCP_PROJECT_ID} > /dev/null 2>&1 || \
  gcloud artifacts repositories create ${ARTIFACT_REPO_NAME} \
    --repository-format=docker \
    --location=${GCP_REGION} \
    --description="Repositorio para imágenes del scraper de Yogonet" \
    --project=${GCP_PROJECT_ID}

# Construir la imagen Docker
IMAGE_TAG="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${ARTIFACT_REPO_NAME}/${IMAGE_NAME}:latest"
echo "Construyendo y subiendo la imagen Docker a: ${IMAGE_TAG}"
gcloud builds submit --region=${GCP_REGION} --tag ${IMAGE_TAG} . --project=${GCP_PROJECT_ID}

echo "Imagen construida y subida exitosamente."

# Desplegar/Actualizar el Job en Cloud Run
echo "Desplegando/Actualizando el Job en Cloud Run: ${JOB_NAME}"
DEPLOY_CMD="gcloud run jobs deploy ${JOB_NAME} \
  --region=${GCP_REGION} \
  --image=${IMAGE_TAG} \
  --memory=${JOB_MEMORY} \
  --cpu=${JOB_CPU} \
  --task-timeout=${JOB_TIMEOUT} \
  --project=${GCP_PROJECT_ID}"

# Añadir cuenta de servicio si se especificó y no está vacía
if [ -n "${SERVICE_ACCOUNT}" ]; then
  echo "Verificando cuenta de servicio: ${SERVICE_ACCOUNT}"
  gcloud iam service-accounts describe ${SERVICE_ACCOUNT} --project=${GCP_PROJECT_ID} > /dev/null 2>&1 || {
    echo "Error: La cuenta de servicio especificada '${SERVICE_ACCOUNT}' no existe en el proyecto '${GCP_PROJECT_ID}'."
    echo "Puedes crearla con: gcloud iam service-accounts create nombre-cuenta --project=${GCP_PROJECT_ID}"
    exit 1
  }
  DEPLOY_CMD="${DEPLOY_CMD} --service-account=${SERVICE_ACCOUNT}"
else
  echo "Usando la cuenta de servicio predeterminada de Compute Engine."
fi

# Ejecutar el comando de despliegue
# Usamos eval para que las variables dentro de DEPLOY_CMD se expandan correctamente
eval ${DEPLOY_CMD}

echo "--- Despliegue Completado ---"
echo "Job '${JOB_NAME}' desplegado/actualizado en la región '${GCP_REGION}'."
echo "Puedes ejecutar el job manualmente desde la consola de Google Cloud o usando:"
echo "gcloud run jobs execute ${JOB_NAME} --region=${GCP_REGION} --project=${GCP_PROJECT_ID}"