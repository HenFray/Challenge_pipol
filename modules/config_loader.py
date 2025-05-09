import configparser
import os

def load_config(config_dir="config", filename="config.ini"):
    """
    Carga la configuración desde un archivo .ini ubicado en un directorio específico.

    Args:
        config_dir (str): El directorio donde se encuentra el archivo de configuración.
        filename (str): El nombre del archivo de configuración.

    Returns:
        configparser.ConfigParser: El objeto de configuración cargado.
                                   Devuelve None si el archivo no se encuentra o hay un error.
    """
    config = configparser.ConfigParser()
    # Construir la ruta completa al archivo de configuración
    config_path = os.path.join(config_dir, filename)

    if not os.path.exists(config_path):
        print(f"Error: El archivo de configuración '{config_path}' no fue encontrado.")
        # Intentar buscar en la raíz como fallback (útil si se ejecuta en un contexto diferente, como Docker sin la subcarpeta)
        if os.path.exists(filename):
            print(f"Intentando cargar '{filename}' desde la raíz...")
            config_path = filename
        else:
            return None # Si no se encuentra en ninguna de las rutas esperadas

    try:
        config.read(config_path)
        print(f"Archivo de configuración '{config_path}' cargado exitosamente.")
        return config
    except Exception as e:
        print(f"Error al leer el archivo de configuración '{config_path}': {e}")
        return None