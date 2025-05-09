import time
import os
import re
import joblib
import pandas as pd
from urllib.parse import urljoin
import traceback

# --- Web Scraping ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- HTML Parsing ---
from bs4 import BeautifulSoup

# --- NLP ---
import nltk

# Verificar/Descargar datos NLTK (simplificado para este script)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Descargando datos NLTK necesarios ('punkt', 'stopwords')...")
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# --- Configuración ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_URL = "https://www.yogonet.com/international/"
BASE_URL = "https://www.yogonet.com"
NEWS_CONTAINER_SELECTOR = "div.contenedor_dato_modulo"
MODEL_FILE = os.path.join(SCRIPT_DIR, 'extractor_model.pkl')

# Carga las stopwords
STOPWORDS = set(stopwords.words('english'))

def get_clean_text(node):
    """Obtiene texto limpio de un nodo BeautifulSoup."""
    return node.get_text(strip=True) if node else ""

def calculate_uppercase_ratio(text):
    """Calcula la proporción de palabras en mayúsculas."""
    try:
        words = word_tokenize(text)
    except Exception: return 0.0
    if not words: return 0.0
    uppercase_words = [w for w in words if w.isupper() and len(w) > 1]
    return len(uppercase_words) / len(words)

def calculate_stopword_ratio(text):
    """Calcula la proporción de stopwords."""
    try:
        words = word_tokenize(text.lower())
    except Exception: return 0.0
    if not words: return 0.0
    stopword_count = sum(1 for w in words if w in STOPWORDS)
    return stopword_count / len(words)


def extract_features(node, soup):
    """Extrae un DICCIONARIO de características para UN nodo (IDÉNTICA A train_model.py)."""
    features = {}
    text = get_clean_text(node)
    parent_node = node.parent if node and hasattr(node, 'parent') and node.parent and node.parent.name != '[document]' else None

    # --- Características  ---
    features['tag_name'] = node.name if node else 'None'
    features['num_children'] = len(node.find_all(recursive=False)) if node else 0
    features['parent_tag'] = parent_node.name if parent_node else 'None'
    features['has_href'] = 1 if node and node.has_attr('href') else 0
    features['has_src'] = 1 if node and node.has_attr('src') else 0
    # No necesitamos 'class_list' directamente si el ColumnTransformer la ignora,
    # pero sí las features derivadas de ella:
    class_list_str = " ".join(node.get('class', [])).lower() if node else ""
    features['text_length'] = len(text)
    features['word_count'] = len(word_tokenize(text)) if text else 0
    features['uppercase_ratio'] = calculate_uppercase_ratio(text) if text else 0.0
    features['stopword_ratio'] = calculate_stopword_ratio(text) if text else 0.0
    features['depth'] = len(list(node.parents)) if node and hasattr(node, 'parents') else 0
    features['is_h2'] = 1 if node and node.name == 'h2' else 0
    features['is_div'] = 1 if node and node.name == 'div' else 0
    features['is_a'] = 1 if node and node.name == 'a' else 0
    features['is_img'] = 1 if node and node.name == 'img' else 0
    features['class_contains_title'] = 1 if 'title' in class_list_str or 'titulo' in class_list_str else 0
    features['class_contains_kicker'] = 1 if 'kicker' in class_list_str or 'volanta' in class_list_str else 0
    features['class_contains_image'] = 1 if 'image' in class_list_str or 'imagen' in class_list_str else 0

    return features 

def setup_driver():
    """Configura e inicia el WebDriver de Selenium."""
    print("Configurando WebDriver...")
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    try:
        try:
             service = ChromeService(ChromeDriverManager().install())
             driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e_wdm:
             print(f"Fallo con webdriver-manager: {e_wdm}")
             print("Intentando ruta local de chromedriver (asegúrate que esté en PATH)...")
             driver = webdriver.Chrome(options=chrome_options)

        print("WebDriver iniciado.")
        return driver
    except Exception as e:
        print(f"Error fatal al iniciar WebDriver: {e}")
        print("Asegúrate que ChromeDriver esté instalado y accesible en el PATH del sistema.")
        return None


def scrape_dynamically_with_model(driver, url, model_pipeline):
    """Realiza el scraping usando el pipeline ML para identificar elementos."""
    print(f"Navegando a {url}...")
    driver.get(url)
    wait = WebDriverWait(driver, 20)
    news_data = []

    try:
        print(f"Esperando los contenedores de noticias ({NEWS_CONTAINER_SELECTOR})...")
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, NEWS_CONTAINER_SELECTOR)))
        time.sleep(2) # Pausa adicional por si hay carga JS lenta
        news_elements_selenium = driver.find_elements(By.CSS_SELECTOR, NEWS_CONTAINER_SELECTOR)
        print(f"Se encontraron {len(news_elements_selenium)} contenedores.")

        if not news_elements_selenium:
            print("No se encontraron contenedores de noticias.")
            return []

        print("Procesando contenedores con el modelo...")
        for i, element_selenium in enumerate(news_elements_selenium):
            print(f"--- Procesando Bloque {i+1} ---")
            try:
                html_content = element_selenium.get_attribute('outerHTML')
                soup = BeautifulSoup(html_content, 'lxml')
                container_node = soup.find(recursive=False)
                if not container_node: container_node = soup

                nodes_to_process = []
                node_feature_list = []
                for node in container_node.find_all(True, recursive=True):
                    if node.name and (node.string is None or node.string.strip()):
                        features_dict = extract_features(node, soup) 
                        node_feature_list.append(features_dict)
                        nodes_to_process.append(node) 

                if not node_feature_list:
                    print(f"  Bloque {i+1}: No se extrajeron features.")
                    continue

                # Convertir lista de diccionarios a DataFrame de Pandas
                features_df = pd.DataFrame(node_feature_list)

                # Predecir roles usando el pipeline cargado
                predicted_roles = model_pipeline.predict(features_df)

                # Combinar nodos con sus predicciones
                predictions = [{'node': node, 'role': role}
                               for node, role in zip(nodes_to_process, predicted_roles)]

                # --- Post-procesamiento de predicciones ---
                title_text, kicker_text, image_url, link_url = "N/A", "N/A", "N/A", "N/A"

                # Lógica de selección
                title_node = next((p['node'] for p in predictions if p['role'] == 'Title'), None)
                kicker_node = next((p['node'] for p in predictions if p['role'] == 'Kicker'), None)
                # Busca específicamente la etiqueta <img> predicha como Image_URL
                image_node = next((p['node'] for p in predictions if p['role'] == 'Image_URL' and p['node'].name == 'img'), None)

                if title_node:
                    title_text = get_clean_text(title_node)
                    # Extraer link si el nodo Title es <a>
                    if title_node.name == 'a' and title_node.has_attr('href'):
                        link_url = urljoin(BASE_URL, title_node.get('href'))

                if kicker_node:
                    kicker_text = get_clean_text(kicker_node)
                    kicker_text = kicker_text if kicker_text else "N/A"

                if image_node:
                    src = image_node.get('src')
                    if src:
                        image_url = urljoin(BASE_URL, src)

                # Fallback para Link: Si no se obtuvo del Title, intentar buscar un <a> alrededor de la imagen
                if link_url == "N/A" and image_node and image_node.parent and image_node.parent.name == 'a' and image_node.parent.has_attr('href'):
                     link_url = urljoin(BASE_URL, image_node.parent.get('href'))

                # Solo añadir si se encontró título (o link si es requisito)
                if title_text != "N/A" and link_url != "N/A":
                    news_data.append({
                        "title": title_text,
                        "kicker": kicker_text,
                        "image_url": image_url,
                        "link": link_url
                        })
                    print(f"  Bloque {i+1}: OK -> T='{title_text[:30]}...', K='{kicker_text[:20]}...', Img={'Sí' if image_url!='N/A' else 'No'}, Link={'Sí' if link_url!='N/A' else 'No'}")
                else:
                     print(f"  Bloque {i+1}: Omitido (Falta Título o Link principal)")


            except Exception as e_inner:
                print(f"Error procesando el bloque {i+1}: {e_inner}")
                traceback.print_exc() # Imprime detalle del error
                continue

    except TimeoutError:
        print("Timeout esperando los elementos.")
    except Exception as e_outer:
        print(f"Error general durante el scraping: {e_outer}")
        traceback.print_exc() # Imprime detalle del error
    finally:
        print("Cerrando WebDriver.")
        if driver:
            driver.quit()

    print(f"\nScraping dinámico finalizado. Se extrajeron {len(news_data)} noticias.")
    return news_data

# --- SCRIPT PRINCIPAL ---
if __name__ == "__main__":
    print("Iniciando Scraper Dinámico con Modelo NLP+DOM...")

    # Cargar el pipeline (modelo + preprocesador) entrenado
    if not os.path.exists(MODEL_FILE):
        print(f"Error: Archivo del modelo '{MODEL_FILE}' no encontrado.")
        exit()

    try:
        print(f"Cargando pipeline desde '{MODEL_FILE}'...")
        # Carga el pipeline completo guardado por joblib
        model_pipeline = joblib.load(MODEL_FILE)
        print("Pipeline cargado exitosamente.")
    except Exception as e:
        print(f"Error al cargar el pipeline: {e}")
        exit()

    # Configurar y ejecutar Selenium
    driver = setup_driver()
    if not driver:
        exit()

    # Realizar scraping usando el pipeline
    scraped_data = scrape_dynamically_with_model(driver, TARGET_URL, model_pipeline)

    # Mostrar resultados (o procesar/guardar)
    if scraped_data:
        print("\n--- Datos Extraídos (primeros 5) ---")
        df_results = pd.DataFrame(scraped_data)
        print(df_results.head().to_string())

        # --- Opcional: Guardar en CSV ---
        try:
            output_dir_pred = os.path.join(SCRIPT_DIR, "output_prediction")
            if not os.path.exists(output_dir_pred):
                 os.makedirs(output_dir_pred)
            csv_path_pred = os.path.join(output_dir_pred, "dynamic_scrape_results.csv")
            df_results.to_csv(csv_path_pred, index=False, encoding='utf-8-sig')
            print(f"\nResultados guardados en: {csv_path_pred}")
        except Exception as e_save:
            print(f"Error al guardar resultados en CSV: {e_save}")



    else:
        print("\nNo se extrajeron datos.")