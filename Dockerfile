# Usar una imagen base de Python
FROM python:3.9-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias para Chrome y webdriver-manager
# Actualizar lista de paquetes e instalar wget y unzip
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    # Dependencias de Chrome
    libglib2.0-0 \
    libnss3 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libexpat1 \
    libgbm1 \
    libgcc1 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    --no-install-recommends \
    # Limpiar cache de apt
    && rm -rf /var/lib/apt/lists/*

# Descargar e instalar Google Chrome estable
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    --no-install-recommends \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de requerimientos e instalar las librerías Python
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación (script y config)
COPY script.py .
COPY config/ config/

# Crear el directorio de salida
RUN mkdir output

# webdriver-manager descargará ChromeDriver automáticamente al ejecutar el script.

# Comando por defecto para ejecutar el script cuando se inicie el contenedor
CMD ["python", "script.py"]