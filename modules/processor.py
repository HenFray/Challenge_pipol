import pandas as pd
import re

def process_data_with_pandas(articles_list):
    """
    Procesa la lista de artículos extraídos usando Pandas para añadir métricas
    como conteo de palabras, caracteres y palabras capitalizadas en el título.

    Args:
        articles_list (list): Lista de diccionarios, cada uno representando un artículo.

    Returns:
        pd.DataFrame: DataFrame con las métricas añadidas.
                      Devuelve un DataFrame vacío si la lista de entrada está vacía.
    """
    if not articles_list:
        print("No hay artículos para procesar con Pandas.")
        return pd.DataFrame() # Devolver DataFrame vacío

    print("\nIniciando post-procesamiento con Pandas...")
    try:
        df = pd.DataFrame(articles_list)

        # Verificar si la columna 'title' existe
        if 'title' not in df.columns:
            print("Advertencia: La columna 'title' no se encuentra en los datos extraídos.")
            # Añadir columnas vacías o con valores por defecto si 'title' no existe
            df['title_word_count'] = 0
            df['title_char_count'] = 0
            df['title_capital_words'] = [[] for _ in range(len(df))]
            return df

        # Crear una columna temporal segura para procesar, manejando NaNs y tipos
        df['title_processed'] = df['title'].fillna('').astype(str)
        # Reemplazar "N/A" específicamente si es necesario después de la conversión
        df.loc[df['title_processed'] == "N/A", 'title_processed'] = ''

        # Calcular métricas
        df['title_word_count'] = df['title_processed'].apply(lambda x: len(x.split()) if x else 0)
        df['title_char_count'] = df['title_processed'].apply(len)

        def get_capitalized_words(title_text):
            """Encuentra palabras que comienzan con mayúscula en un texto."""
            if not title_text:
                return []
            # Expresión regular para encontrar palabras que empiezan con mayúscula
            # Incluye apóstrofes y guiones dentro de las palabras
            return re.findall(r'\b[A-Z][a-zA-Z\'-]*\b', title_text)

        df['title_capital_words'] = df['title_processed'].apply(get_capitalized_words)

        # Eliminar la columna temporal
        df.drop(columns=['title_processed'], inplace=True)

        print("Post-procesamiento con Pandas finalizado.")
        return df
    except Exception as e:
        print(f"Error durante el procesamiento con Pandas: {e}")
        # En caso de error, devolver el DataFrame original si es posible
        # o uno vacío si la creación inicial falló
        return pd.DataFrame(articles_list) if 'df' not in locals() else df