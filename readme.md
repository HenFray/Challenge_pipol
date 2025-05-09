# Proyecto Scraper Yogonet

Este proyecto contiene scripts para realizar scraping de noticias del sitio Yogonet, procesarlas y, opcionalmente, cargarlas a BigQuery. También incluye un scraper alternativo que utiliza un modelo de Machine Learning para la extracción de datos.

## Tabla de Contenidos
* [Prerrequisitos](#prerrequisitos)
* [Configuración](#configuración)
* [Uso con Docker](#uso-con-docker)
* [Uso Local (Sin Docker)](#uso-local-sin-docker)
    * [Ejecutar el Scraper Principal (`main.py`)](#ejecutar-el-scraper-principal-mainpy)
    * [Ejecutar el Scraper con Modelo ML (`model_ML/scraper_model_ml.py`)](#ejecutar-el-scraper-con-modelo-ml-model_mlscraper_model_mlpy)
* [Scripts Adicionales](#scripts-adicionales)
    * [Despliegue en GCP (`deploy.sh`)](#despliegue-en-gcp-deploysh)
    * [Entrenamiento del Modelo ML](#entrenamiento-del-modelo-ml)

## Prerrequisitos

* Python 3.x
* Docker (si se utiliza la opción de Docker)
* Google Chrome y ChromeDriver (para `main.py` y `model_ML/scraper_model_ml.py` si se ejecutan localmente y no están ya en el PATH o especificados en el Dockerfile)
* Dependencias listadas en `requirements.txt`. Instalarlas con:
    ```bash
    pip install -r requirements.txt
    ```

## Configuración

El proyecto utiliza un archivo de configuración principal `config/config.ini`. Antes de ejecutar los scripts, asegúrate de revisar y actualizar este archivo, especialmente las secciones:

* **`[bigquery]`**:
    * `project_id`: Tu ID de proyecto de Google Cloud.
    * `dataset_id`: Tu ID de dataset en BigQuery.
    * `table_id`: Tu ID de tabla en BigQuery.
* **`[settings]`**:
    * `output_csv_filename`: Nombre del archivo CSV para guardar los datos procesados localmente (ej: `yogonet_news_data.csv` [cite: 1]).
* **`[gcp_deploy]`** (para el script `deploy.sh`):
    * `project_id`: ID del proyecto de GCP para el despliegue.
    * `region`: Región para Cloud Run, Artifact Registry, etc.
    * `service_account`: Cuenta de servicio (opcional).
    * `artifact_repo_name`: Nombre del repositorio en Artifact Registry.
    * `image_name`: Nombre base de la imagen Docker.
    * `job_name`: Nombre del Job en Cloud Run.
    * `memory`: Límite de memoria para el Job.
    * `cpu`: Límite de CPU para el Job.

El script `deploy.sh` también espera un archivo `config/config_deploy.env` que debe ser creado a partir de las variables de `[gcp_deploy]` en `config.ini` o definido directamente. Si `config_deploy.env` no existe, el script `deploy.sh` mostrará un error.

## Uso con Docker

Para construir y ejecutar la imagen Docker, utiliza los siguientes comandos. **Nota:** Necesitarás un `Dockerfile` en la raíz de tu proyecto para que estos comandos funcionen. El contenido del `Dockerfile` definirá cómo se construye la imagen y qué script se ejecuta por defecto.

1.  **Construir la imagen Docker:**
    Esto construirá la imagen con el tag `pipol`.
    ```bash
    docker buildx build -t pipol .
    ```

2.  **Ejecutar el contenedor Docker:**
    Esto ejecutará el comando por defecto especificado en el `ENTRYPOINT` o `CMD` de tu `Dockerfile` (probablemente `python main.py` [cite: 7]).
    ```bash
    docker run --rm pipol
    ```
    * Para ejecutar `model_ML/scraper_model_ml.py` dentro de Docker, puedes:
        * Modificar el `Dockerfile` para que este sea el script por defecto.
        * O, si el `Dockerfile` está configurado para aceptar comandos, pasar el comando al `docker run`:
            ```bash
            # Asumiendo que el ENTRYPOINT del Dockerfile es "python"
            # o que el script es ejecutable y está en el PATH
            docker run --rm pipol python model_ML/scraper_model_ml.py
            ```

## Uso Local (Sin Docker)

### Ejecutar el Scraper Principal (`main.py`)

El script `main.py` es el punto de entrada principal para el proceso de scraping tradicional (usando `modules/scraper.py` [cite: 8, 7]), procesamiento (`modules/processor.py` [cite: 9, 7]) y carga a BigQuery (`modules/bigquery_handler.py` [cite: 11, 7]).

1.  **Asegúrate de tener las dependencias instaladas:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configura `config/config.ini`** [cite: 1] como se describió anteriormente, especialmente las credenciales y configuración de BigQuery si deseas usar esa funcionalidad.
3.  **Ejecuta el script:**
    ```bash
    python main.py
    ```
    El script realizará las siguientes acciones:
    * Cargará la configuración desde `config/config.ini`[cite: 10, 7].
    * Ejecutará el scraper (`modules/scraper.py` [cite: 8, 7]).
    * Procesará los datos extraídos (`modules/processor.py` [cite: 9, 7]).
    * Guardará los resultados en un archivo CSV en la carpeta `output/` (el nombre del archivo se toma de `config.ini`, ej: `output/yogonet_news_data.csv` [cite: 1, 7]).
    * Intentará cargar los datos procesados a BigQuery si la configuración en `config.ini` [cite: 1] está completa y no son los valores placeholder (`modules/bigquery_handler.py` [cite: 11, 7]).

### Ejecutar el Scraper con Modelo ML (`model_ML/scraper_model_ml.py`)

El script `model_ML/scraper_model_ml.py` [cite: 6] utiliza un modelo de Machine Learning pre-entrenado (`model_ML/extractor_model.pkl`) para identificar y extraer datos de la página.

1.  **Asegúrate de tener las dependencias instaladas**, incluyendo las específicas para ML (ej. `scikit-learn`, `nltk`, `joblib`). Estas deberían estar incluidas en `requirements.txt`[cite: 13].
2.  **Asegúrate de que el modelo entrenado `extractor_model.pkl` exista** en la carpeta `model_ML/`. Si no existe, necesitarás entrenarlo primero (ver sección [Entrenamiento del Modelo ML](#entrenamiento-del-modelo-ml)).
3.  **El script intentará descargar los datos necesarios de NLTK (`punkt`, `stopwords`) automáticamente.** Si esto falla, puedes intentar descargarlos manualmente en un intérprete de Python:
    ```python
    import nltk
    nltk.download('punkt')
    nltk.download('stopwords')
    ```
4.  **Ejecuta el script:**
    ```bash
    python model_ML/scraper_model_ml.py
    ```
    El script realizará las siguientes acciones:
    * Cargará el pipeline del modelo ML entrenado.
    * Utilizará Selenium para navegar a la URL de Yogonet y extraer el HTML de los bloques de noticias.
    * Para cada bloque, aplicará el modelo ML para predecir qué nodos HTML corresponden al título, kicker, URL de imagen y enlace.
    * Procesará estas predicciones para extraer el contenido[cite: 6].
    * Mostrará los primeros 5 resultados extraídos en la consola[cite: 6].
    * Guardará todos los resultados extraídos en un archivo CSV en `model_ML/output_prediction/dynamic_scrape_results.csv`.

## Scripts Adicionales

### Despliegue en GCP (`deploy.sh`)

El script `deploy.sh` [cite: 16] está diseñado para automatizar el proceso de construcción de la imagen Docker, subirla a Google Artifact Registry y desplegarla como un Cloud Run Job.

1.  **Configura Google Cloud SDK (`gcloud`)** en tu máquina y autentícate con una cuenta que tenga los permisos necesarios (roles/artifactregistry.writer, roles/run.admin, roles/cloudbuild.builds.editor, roles/iam.serviceAccountUser si usas una cuenta de servicio específica).
2.  **Crea un archivo `config/config_deploy.env`** o asegúrate de que la sección `[gcp_deploy]` en `config.ini` [cite: 1] esté completa y que el script `deploy.sh` [cite: 16] esté adaptado para leer de la fuente correcta. El script proporcionado espera `config/config_deploy.env`.
    Un ejemplo de `config/config_deploy.env`:
    ```env
    GCP_PROJECT_ID="tu-proyecto-gcp"
    GCP_REGION="us-central1"
    # SERVICE_ACCOUNT="tu-cuenta-servicio@tu-proyecto-gcp.iam.gserviceaccount.com" # Opcional, si no se usa la default
    ARTIFACT_REPO_NAME="yogonet-scraper-repo"
    IMAGE_NAME="yogonet-scraper"
    JOB_NAME="yogonet-scraper-job"
    JOB_MEMORY="512Mi"
    JOB_CPU="1"
    JOB_TIMEOUT="600s" # Ejemplo de timeout para el job
    ```
    **Importante:** Reemplaza los valores placeholder con tu configuración real.
3.  **Asegúrate de que el script `deploy.sh` [cite: 16] tenga permisos de ejecución:**
    ```bash
    chmod +x deploy.sh
    ```
4.  **Ejecuta el script desde la raíz del proyecto:**
    ```bash
    ./deploy.sh
    ```
    El script realizará:
    * Configuración de `gcloud` para el proyecto[cite: 16].
    * Habilitación de APIs necesarias[cite: 16].
    * Creación (si no existe) del repositorio en Artifact Registry[cite: 16].
    * Construcción y subida de la imagen Docker usando Cloud Build[cite: 16].
    * Despliegue o actualización del Job en Cloud Run[cite: 16].

### Entrenamiento del Modelo ML

Los scripts para entrenar el modelo de Machine Learning se encuentran en la carpeta `model_ML/training_model/`:

1.  **`collect_html_for_training.py`**[cite: 5]:
    * **Propósito**: Este script usa Selenium para navegar a la URL de Yogonet especificada (actualmente `https://www.yogonet.com/international/`) y guarda bloques HTML individuales de los artículos de noticias. Estos bloques se utilizan como datos base para el etiquetado manual.
    * **Salida**: Los archivos HTML se guardan en `model_ML/training_model/training_data/html_blocks/` con nombres como `block_1.html`, `block_2.html`, etc.[cite: 3, 4].
    * **Ejecución**:
        ```bash
        python model_ML/training_model/collect_html_for_training.py
        ```

2.  **`labels.json`**[cite: 18]:
    * **Propósito**: Este archivo es crucial y **debe ser creado o actualizado manualmente** después de ejecutar `collect_html_for_training.py`[cite: 5]. Contiene las "etiquetas" o la "verdad fundamental" para el entrenamiento. Para cada archivo `block_X.html` guardado, debes inspeccionar su contenido y identificar los XPaths precisos de los elementos que corresponden al título, kicker, y la URL de la imagen.
    * **Formato**: Es un JSON donde cada clave es el nombre del archivo HTML (ej. `"block_1.html"`) y el valor es una lista de objetos, cada uno especificando el `xpath` del elemento y su `role` (ej. `"Title"`, `"Kicker"`, `"Image_URL"`).
        *Los XPaths deben ser relativos al contenido del bloque HTML individual.*
    * **Ejemplo de una entrada en `labels.json`**[cite: 18]:
        ```json
        {
          "block_1.html": [
            { "xpath": "/body[1]/div[1]/div[1]/div[1]", "role": "Kicker" },
            { "xpath": "/body[1]/div[1]/div[1]/h2[1]/a[1]", "role": "Title" },
            { "xpath": "/body[1]/div[1]/div[2]/a[1]/img[1]", "role": "Image_URL"}
          ],
          // ... más bloques
        }
        ```

3.  **`train_model.py`**[cite: 17]:
    * **Propósito**: Este script es el corazón del proceso de entrenamiento. Realiza lo siguiente:
        * Carga las etiquetas desde `labels.json`[cite: 18, 17].
        * Lee cada bloque HTML referenciado en `labels.json`[cite: 17].
        * Para cada nodo dentro de los bloques HTML, extrae un conjunto de características (nombre de la etiqueta, número de hijos, clases CSS, longitud del texto, etc.)[cite: 17].
        * Asocia estas características con el `role` (etiqueta) correspondiente del archivo `labels.json`[cite: 17].
        * Preprocesa las características (escalado para numéricas, one-hot encoding para categóricas)[cite: 17].
        * Entrena un modelo clasificador (RandomForestClassifier en este caso) para predecir el `role` de un nodo HTML basado en sus características[cite: 17].
    * **Salida**: El pipeline completo del modelo entrenado (que incluye el preprocesador y el clasificador) se guarda como `model_ML/extractor_model.pkl`[cite: 17]. Este archivo es el que luego utiliza `model_ML/scraper_model_ml.py`[cite: 6].
    * **Ejecución**:
        ```bash
        python model_ML/training_model/train_model.py
        ```
    * **Nota sobre NLTK**: El script `train_model.py` [cite: 17] intentará verificar y descargar los recursos `stopwords` de NLTK si no los encuentra. Si la descarga automática falla, es posible que necesites ejecutarla manualmente en un intérprete de Python como se mencionó anteriormente.