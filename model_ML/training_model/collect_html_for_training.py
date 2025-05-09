import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURACIÓN ---
TARGET_URL = "https://www.yogonet.com/international/"
NEWS_CONTAINER_SELECTOR = "div.contenedor_dato_modulo" # Selector inicial para los bloques
OUTPUT_DIR = "training_data/html_blocks" # Directorio para guardar los HTML
MAX_BLOCKS_TO_SAVE = 50 # Limita cuántos bloques guardar para empezar

def setup_driver():
    """Configura e inicia el WebDriver de Selenium."""
    print("Configurando WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("WebDriver iniciado.")
        return driver
    except Exception as e:
        print(f"Error al iniciar WebDriver: {e}")
        return None

def collect_html_blocks(driver, url, output_dir, max_blocks):
    """Navega, extrae y guarda los bloques HTML de noticias."""
    print(f"Navegando a {url}...")
    driver.get(url)
    wait = WebDriverWait(driver, 20)
    saved_count = 0

    # Crear directorio de salida si no existe
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Directorio creado: '{output_dir}'")

    try:
        print(f"Esperando los contenedores de noticias ({NEWS_CONTAINER_SELECTOR})...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, NEWS_CONTAINER_SELECTOR)))
        news_elements_selenium = driver.find_elements(By.CSS_SELECTOR, NEWS_CONTAINER_SELECTOR)
        print(f"Se encontraron {len(news_elements_selenium)} contenedores.")

        if not news_elements_selenium:
            print("No se encontraron contenedores de noticias.")
            return 0

        print(f"Guardando hasta {max_blocks} bloques HTML en '{output_dir}'...")
        for i, element_selenium in enumerate(news_elements_selenium):
            if saved_count >= max_blocks:
                print(f"Límite de {max_blocks} bloques alcanzado.")
                break
            try:
                html_content = element_selenium.get_attribute('outerHTML')
                file_path = os.path.join(output_dir, f"block_{i+1}.html")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                saved_count += 1
            except Exception as e_inner:
                print(f"Error guardando el bloque {i+1}: {e_inner}")
                continue # Pasar al siguiente bloque

    except TimeoutError:
        print("Timeout esperando los elementos.")
    except Exception as e_outer:
        print(f"Error general durante la recolección: {e_outer}")
    finally:
        print("Cerrando WebDriver.")
        if driver:
            driver.quit()

    print(f"\nRecolección finalizada. Se guardaron {saved_count} bloques HTML.")
    return saved_count

# --- SCRIPT PRINCIPAL ---
if __name__ == "__main__":
    print("Iniciando script de recolección de HTML para entrenamiento...")

    driver = setup_driver()
    if not driver:
        exit()

    num_saved = collect_html_blocks(driver, TARGET_URL, OUTPUT_DIR, MAX_BLOCKS_TO_SAVE)

    if num_saved > 0:
        print(f"\nArchivos HTML guardados en la carpeta: '{OUTPUT_DIR}'")
    else:
        print("\nNo se guardaron archivos HTML. Revisa posibles errores.")