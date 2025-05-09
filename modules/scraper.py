import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin

def scrape_yogonet():
    """
    Extrae datos del portal de noticias Yogonet International.
    Utiliza selectores actualizados basados en la estructura HTML proporcionada.

    returns:
        :rtype: list
        list: Una lista de diccionarios, donde cada diccionario contiene
              el 'title', 'kicker', 'image_url', y 'link' de un artículo de noticias.
              Devuelve una lista vacía si el scraping falla o no se encuentran artículos.
    """
    print("Iniciando el proceso de scraping con selectores actualizados...")

    # Configuración de las opciones de Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    driver = None # Inicializar driver a None
    try:
        # Configurar ChromeDriver
        print("Instalando/Actualizando ChromeDriver...")
        service = ChromeService(ChromeDriverManager().install())
        print("ChromeDriver listo.")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("WebDriver iniciado correctamente.")
    except Exception as e:
        print(f"Error al iniciar WebDriver: {e}")
        print("Asegúrate de que Google Chrome y ChromeDriver estén correctamente instalados y en el PATH,")
        print("o que la ruta del binario de Chrome esté especificada en las opciones si ejecutas en Docker.")
        return []

    # URL de destino y almacenamiento de datos
    url = "https://www.yogonet.com/international/"
    news_data = []
    base_url = "https://www.yogonet.com" # Para construir URLs absolutas

    try:
        print(f"Navegando a {url}...")
        driver.get(url)
        wait = WebDriverWait(driver, 30)
        news_container_selector = "div.contenedor_dato_modulo"
        print(f"Esperando a que los elementos '{news_container_selector}' se carguen...")
        # Esperar a que al menos un elemento esté presente
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, news_container_selector)))
        print("Elementos encontrados, procediendo a extraer...")
        # Pausa breve adicional si es necesario para renderizado dinámico
        time.sleep(2)
        news_elements = driver.find_elements(By.CSS_SELECTOR, news_container_selector)
        print(f"Se encontraron {len(news_elements)} elementos de noticias potenciales.")

        if not news_elements:
            print("No se encontraron elementos de noticias con el selector principal.")

        for i, news_item_container in enumerate(news_elements):
            title, kicker, image_url, link = "N/A", "N/A", "N/A", "N/A"
            try:
                # Extraer Kicker (si existe)
                try:
                    kicker_element = news_item_container.find_element(By.CSS_SELECTOR, "div.volanta_titulo div.volanta.fuente_roboto_slab")
                    kicker = kicker_element.text.strip()
                except: pass # Ignorar si no se encuentra

                # Extraer Título y Enlace (priorizando el <a> dentro del <h2>)
                try:
                    title_link_element = news_item_container.find_element(By.CSS_SELECTOR, "div.volanta_titulo h2.titulo.fuente_roboto_slab a")
                    title = title_link_element.text.strip()
                    link_raw = title_link_element.get_attribute("href")
                    if link_raw: link = urljoin(base_url, link_raw)
                except:
                    # Fallback: Extraer título del <h2> directamente (si no tiene <a>)
                    try:
                        title_element_fallback = news_item_container.find_element(By.CSS_SELECTOR, "div.volanta_titulo h2.titulo.fuente_roboto_slab")
                        title = title_element_fallback.text.strip()
                        # Intentar obtener el enlace de un <a> general si aún no se tiene
                        if link == "N/A":
                            try:
                                # Buscar el primer <a> dentro del contenedor (más genérico)
                                link_general_element = news_item_container.find_element(By.TAG_NAME, "a")
                                link_raw = link_general_element.get_attribute("href")
                                if link_raw and link_raw.startswith(("http", "/")):
                                    link = urljoin(base_url, link_raw)
                            except: pass
                    except: pass # Ignorar si no se encuentra título

                # Extraer URL de imagen (probando dos selectores comunes)
                try:
                    image_element = news_item_container.find_element(By.CSS_SELECTOR, "div.imagen a img")
                    image_url_raw = image_element.get_attribute("src")
                    if image_url_raw: image_url = urljoin(base_url, image_url_raw)
                except:
                    try:
                        # Fallback: Buscar <img> directamente en div.imagen
                        image_element_fallback = news_item_container.find_element(By.CSS_SELECTOR, "div.imagen img")
                        image_url_raw = image_element_fallback.get_attribute("src")
                        if image_url_raw: image_url = urljoin(base_url, image_url_raw)
                    except: pass # Ignorar si no se encuentra imagen

                # Asegurarse de que al menos título y enlace sean válidos
                if title and title != "N/A" and link and link != "N/A":
                    news_data.append({"title": title, "kicker": kicker, "image_url": image_url, "link": link})

            except Exception as e:
                print(f"Error procesando un artículo (índice {i}): {e}. Detalles: T:{title},L:{link},I:{image_url},K:{kicker}")
                continue # Saltar al siguiente elemento

        if not news_data: print("No se pudo extraer ninguna noticia válida.")

    except TimeoutError as te: print(f"Timeout esperando los elementos: {te}")
    except Exception as e: print(f"Ocurrió un error durante el scraping: {e}")
    finally:
        print("Cerrando el WebDriver.")
        if driver: driver.quit()
    print(f"Scraping finalizado. Se extrajeron {len(news_data)} noticias.")
    return news_data