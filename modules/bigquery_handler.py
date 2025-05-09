from google.cloud import bigquery
import pandas as pd

def load_df_to_bigquery(dataframe, project_id, dataset_id, table_id):
    """
    Carga un DataFrame de Pandas a una tabla de BigQuery.
    La tabla se creará si no existe y se añadirán los datos (append).

    Args:
        dataframe (pd.DataFrame): El DataFrame a cargar.
        project_id (str): El ID del proyecto de Google Cloud.
        dataset_id (str): El ID del dataset de BigQuery.
        table_id (str): El ID de la tabla de BigQuery.
    """
    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        print("DataFrame vacío o inválido, no se cargará nada a BigQuery.")
        return

    # Configurar el ID completo de la tabla
    table_full_id = f"{project_id}.{dataset_id}.{table_id}"
    print(f"Intentando cargar datos a BigQuery tabla: {table_full_id}")

    try:
        # Inicializar el cliente de BigQuery.
        client = bigquery.Client(project=project_id)
        print(f"Cliente de BigQuery inicializado para el proyecto: {client.project}")

        # Configuración del Job de carga
        job_config = bigquery.LoadJobConfig(
            # WRITE_APPEND añade los datos a la tabla existente.
            # WRITE_TRUNCATE borraría la tabla y la reemplazaría.
            write_disposition="WRITE_TRUNCATE",
            # CREATE_IF_NEEDED crea la tabla si no existe.
            # CREATE_NEVER falla si la tabla no existe.
            create_disposition="CREATE_IF_NEEDED",
            # Autodetectar esquema basado en el DataFrame
            autodetect=True
        )

        print("Iniciando job de carga a BigQuery...")
        # Cargar el DataFrame a BigQuery
        job = client.load_table_from_dataframe(
            dataframe, table_full_id, job_config=job_config
        )
        job.result()  # Esperar a que el job termine

        # Verificar el resultado
        table = client.get_table(table_full_id)  # Obtener la tabla actualizada
        print(
            f"Cargados {job.output_rows} filas. Total de filas en la tabla {table_full_id}: {table.num_rows}."
        )
        print(f"Esquema de la tabla ({len(table.schema)} columnas): {[(field.name, field.field_type) for field in table.schema]}")


    except Exception as e:
        print(f"Error al cargar datos a BigQuery: {e}")
        print(f"  - Detalles del error: {type(e).__name__}")