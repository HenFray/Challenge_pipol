import os
import json
import pandas as pd
from bs4 import BeautifulSoup
import nltk
import joblib
import re
import traceback


# --- Forzar descarga/verificación de NLTK 'stopwords' ---
try:
    print("Verificando/Descargando recurso NLTK 'stopwords'...")
    nltk.data.find('corpora/stopwords')
    print("Recurso 'stopwords' encontrado.")
except LookupError:
    print("Recurso 'stopwords' no encontrado. Descargando...")
    try:
        nltk.download('stopwords', quiet=False)
        print("Descarga de 'stopwords' completada.")
        nltk.data.find('corpora/stopwords') # Verificar de nuevo
    except Exception as e_download:
         print(f"\nError durante la descarga de NLTK 'stopwords': {e_download}")
         exit()

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# --- Machine Learning Imports ---
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline 
from sklearn.metrics import classification_report
from sklearn.exceptions import NotFittedError

# --- Configuración (con rutas relativas al script) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.join(SCRIPT_DIR, "training_data", "html_blocks")
LABELS_FILE = os.path.join(SCRIPT_DIR, "labels.json")
MODEL_OUTPUT_FILE = os.path.join(SCRIPT_DIR, "extractor_model.pkl")

# Carga las stopwords (después de asegurar que existen)
STOPWORDS = set(stopwords.words('english'))

# --- Funciones de Extracción de Características ---

def get_clean_text(node):
    """Obtiene texto limpio de un nodo BeautifulSoup."""
    return node.get_text(strip=True) if node else ""

def calculate_uppercase_ratio(text):
    """Calcula la proporción de palabras en mayúsculas."""
    try:
        words = word_tokenize(text)
    except Exception as e_tok:
        return 0.0
    if not words:
        return 0.0
    uppercase_words = [w for w in words if w.isupper() and len(w) > 1]
    return len(uppercase_words) / len(words)

def calculate_stopword_ratio(text):
    """Calcula la proporción de stopwords."""
    try:
        words = word_tokenize(text.lower())
    except Exception as e_tok:
        return 0.0
    if not words:
        return 0.0
    stopword_count = sum(1 for w in words if w in STOPWORDS)
    return stopword_count / len(words)

def generate_stable_xpath(node):
    """Genera un XPath posicional simple."""
    path = []
    current = node
    while current is not None and hasattr(current, 'parent') and current.parent is not None and current.parent.name != '[document]':
        try:
            tag_name = current.name
            siblings = [sib for sib in current.parent.find_all(tag_name, recursive=False)]
            node_index = siblings.index(current) + 1
            path.append(f"{tag_name}[{node_index}]")
        except ValueError:
             path.append(f"{current.name}[1]") # Fallback
             break
        current = current.parent
        if current is None or not hasattr(current, 'parent') or current.parent is None:
            break
    if not path and node and node.name:
        path.append(f"{node.name}[1]")
    return "/" + "/".join(reversed(path)) if path else ""


def extract_features_for_training(node, soup):
    """Extrae un DICCIONARIO de características para UN nodo."""
    features = {}
    text = get_clean_text(node)
    parent_node = node.parent if node and hasattr(node, 'parent') and node.parent and node.parent.name != '[document]' else None

    # --- Características ---
    features['tag_name'] = node.name if node else 'None'
    features['num_children'] = len(node.find_all(recursive=False)) if node else 0
    features['parent_tag'] = parent_node.name if parent_node else 'None'
    features['has_href'] = 1 if node and node.has_attr('href') else 0
    features['has_src'] = 1 if node and node.has_attr('src') else 0
    features['class_list'] = " ".join(node.get('class', [])) if node else ""
    features['text_length'] = len(text)
    features['word_count'] = len(word_tokenize(text)) if text else 0
    features['uppercase_ratio'] = calculate_uppercase_ratio(text) if text else 0.0
    features['stopword_ratio'] = calculate_stopword_ratio(text) if text else 0.0
    features['depth'] = len(list(node.parents)) if node and hasattr(node, 'parents') else 0
    features['is_h2'] = 1 if node and node.name == 'h2' else 0
    features['is_div'] = 1 if node and node.name == 'div' else 0
    features['is_a'] = 1 if node and node.name == 'a' else 0
    features['is_img'] = 1 if node and node.name == 'img' else 0
    features['class_contains_title'] = 1 if 'title' in features['class_list'].lower() or 'titulo' in features['class_list'].lower() else 0
    features['class_contains_kicker'] = 1 if 'kicker' in features['class_list'].lower() or 'volanta' in features['class_list'].lower() else 0
    features['class_contains_image'] = 1 if 'image' in features['class_list'].lower() or 'imagen' in features['class_list'].lower() else 0

    features['xpath'] = generate_stable_xpath(node)

    return features

# --- Proceso Principal de Entrenamiento ---
if __name__ == "__main__":
    print("Iniciando proceso de entrenamiento del modelo...")

    # 1. Cargar Etiquetas
    print(f"Cargando etiquetas desde {LABELS_FILE}...")
    try:
        with open(LABELS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            content_no_comments = re.sub(r"//.*", "", content)
            labels_data = json.loads(content_no_comments)
        print(f"Etiquetas cargadas para {len(labels_data)} archivos.")
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de etiquetas '{LABELS_FILE}'.")
        exit()
    except json.JSONDecodeError as e:
        print(f"Error al decodificar JSON en '{LABELS_FILE}': {e}")
        exit()
    except Exception as e:
        print(f"Error inesperado al cargar etiquetas: {e}")
        exit()

    # 2. Extraer Características y Crear Dataset
    print("Procesando archivos HTML y extrayendo características...")
    all_node_data = []

    for filename, labels in labels_data.items():
        filepath = os.path.join(HTML_DIR, filename)
        if not os.path.exists(filepath):
            print(f"Advertencia: Archivo HTML '{filepath}' no encontrado, omitiendo.")
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, 'lxml')
            container_node = next(soup.children, None)
            if not container_node or not hasattr(container_node, 'find_all'):
                 container_node = soup

            label_map = {item['xpath']: item['role'] for item in labels}
            nodes_processed_in_block = 0

            for node in container_node.find_all(True, recursive=True):
                if not node.name or (isinstance(node, str) and not node.strip()): continue

                features_dict = extract_features_for_training(node, soup)
                node_xpath = features_dict.pop('xpath')
                role = label_map.get(node_xpath, 'Other')

                features_dict['role'] = role
                all_node_data.append(features_dict)
                nodes_processed_in_block +=1

        except Exception as e:
            print(f"\nError procesando el archivo '{filename}': {e}")
            traceback.print_exc()
            continue

    if not all_node_data:
        print("Error: No se pudieron extraer características/datos.")
        exit()

    # Crear DataFrame y limpiar NaNs
    df = pd.DataFrame(all_node_data)
    for col in df.columns:
        if df[col].isnull().any():
             if pd.api.types.is_numeric_dtype(df[col]): df[col] = df[col].fillna(0)
             else: df[col] = df[col].fillna('Missing')

    print(f"\nDataset creado con {len(df)} nodos y {len(df.columns)-1} características.")
    print("Distribución de Roles:")
    print(df['role'].value_counts())

    # Verificar muestras
    min_samples = 5
    role_counts = df['role'].value_counts()
    print(f"\nVerificando muestras por clase (mínimo requerido={min_samples}):")
    classes_to_train = ['Title', 'Kicker', 'Image_URL', 'Other']
    for role in classes_to_train:
        count = role_counts.get(role, 0)
        print(f" - {role}: {count} muestras")
        if role != 'Other' and count < min_samples:
            print(f"   ¡ADVERTENCIA! Pocas muestras para la clase '{role}'.")

    # 3. Preprocesamiento y Pipeline
    print("\nDefiniendo pipeline de preprocesamiento y modelo...")

    numeric_features = ['num_children', 'text_length', 'word_count', 'uppercase_ratio', 'stopword_ratio', 'depth']
    binary_features = ['has_href', 'has_src', 'is_h2', 'is_div', 'is_a', 'is_img', 'class_contains_title', 'class_contains_kicker', 'class_contains_image']
    categorical_features = ['tag_name', 'parent_tag']

    numeric_transformer = Pipeline(steps=[('scaler', StandardScaler())])
    categorical_transformer = Pipeline(steps=[('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features),
            ('binary', 'passthrough', binary_features)
        ],
        remainder='drop'
    )

    classifier = RandomForestClassifier(n_estimators=150, random_state=42, class_weight='balanced', max_depth=25, min_samples_leaf=2, n_jobs=-1)

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', classifier)
    ])

    # 4. Separar Datos y Entrenar
    print("Separando datos y entrenando el pipeline...")
    X = df.drop('role', axis=1)
    y = df['role']

    counts = y.value_counts()
    min_samples_for_split = 2
    valid_classes_for_split = counts[counts >= min_samples_for_split].index
    valid_indices = y[y.isin(valid_classes_for_split)].index

    if len(valid_indices) < len(X):
        print(f"Advertencia: Descartando {len(X)-len(valid_indices)} muestras para split.")
        X_filtered = X.loc[valid_indices]
        y_filtered = y.loc[valid_indices]
    else:
        X_filtered = X
        y_filtered = y

    if len(X_filtered) < 10 or len(y_filtered.unique()) < 2:
         print("Error: No hay suficientes datos o clases válidas para entrenar después del filtrado.")
         exit() # Detener aquí si no hay datos válidos

    try:
       X_train, X_test, y_train, y_test = train_test_split(X_filtered, y_filtered, test_size=0.3, random_state=42, stratify=y_filtered)
    except ValueError as e_split:
         print(f"Error durante train_test_split: {e_split}. Intentando sin stratify...")
         X_train, X_test, y_train, y_test = train_test_split(X_filtered, y_filtered, test_size=0.3, random_state=42)

    pipeline.fit(X_train, y_train)
    print("Entrenamiento completado.")

    # 5. Evaluar
    print("\nEvaluando el modelo en el conjunto de prueba...")
    try:
        predictions = pipeline.predict(X_test)
        unique_labels = sorted(list(set(y_test) | set(predictions)))
        print(classification_report(y_test, predictions, labels=unique_labels, zero_division=0))
    except NotFittedError:
         print("Error: El pipeline no fue ajustado.")
    except Exception as e_eval:
         print(f"Error durante la evaluación: {e_eval}")

    # 6. Guardar
    print(f"\nGuardando el pipeline entrenado en '{MODEL_OUTPUT_FILE}'...")
    try:
        joblib.dump(pipeline, MODEL_OUTPUT_FILE)
        print("Pipeline guardado exitosamente.")
        print(f"\n¡Listo! Puedes usar '{MODEL_OUTPUT_FILE}' con 'dynamic_scraper_nlp.py'.")
    except Exception as e_save:
        print(f"Error al guardar el pipeline: {e_save}")