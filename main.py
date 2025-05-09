import os
import modules.config_loader as config_loader
import modules.scraper as scraper
import modules.processor as processor
import modules.bigquery_handler as bigquery_handler

if __name__ == "__main__":
    print("Iniciando script principal...")

    # --- 1. Cargar Configuración ---
    config = config_loader.load_config(config_dir="config", filename="config.ini")

    if not config:
        print("No se pudo cargar la configuración. Saliendo del script.")
        exit()

    # --- Ejecutar Scraping ---
    scraped_articles_list = scraper.scrape_yogonet()

    if scraped_articles_list:
        # --- Procesar Datos ---
        processed_df = processor.process_data_with_pandas(scraped_articles_list)

        if not processed_df.empty:
            print("\n--- DataFrame Procesado (primeras 5 filas) ---")
            print(processed_df.head())

            # --- Guardar Resultados Localmente (Opcional) ---
            try:
                output_dir = "output"
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    print(f"Directorio '{output_dir}' creado.")

                # Leer nombre del archivo CSV desde la configuración
                csv_filename = config.get('settings', 'output_csv_filename', fallback='yogonet_news_data.csv')
                csv_filepath = os.path.join(output_dir, csv_filename)
                processed_df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
                print(f"\nDataFrame procesado guardado localmente en: {csv_filepath}")
            except (KeyError, configparser.NoSectionError):
                 print("\nAdvertencia: Sección [settings] o clave 'output_csv_filename' no encontrada en config.ini.")
                 print("Se usará el nombre de archivo predeterminado 'yogonet_news_data.csv' para el CSV local.")
                 csv_filepath = os.path.join(output_dir, 'yogonet_news_data.csv')
                 try:
                     processed_df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
                     print(f"\nDataFrame procesado guardado localmente en: {csv_filepath}")
                 except Exception as e_csv:
                     print(f"Error al guardar el DataFrame en CSV local con nombre predeterminado: {e_csv}")
            except Exception as e:
                print(f"Error al guardar el DataFrame en CSV local: {e}")

            # --- Cargar a BigQuery ---
            try:
                # Leer configuración de BigQuery
                project_id = config.get('bigquery', 'project_id')
                dataset_id = config.get('bigquery', 'dataset_id')
                table_id = config.get('bigquery', 'table_id')

                # Validar que no sean los valores placeholder
                if project_id and dataset_id and table_id:
                    if project_id.startswith("TU_") or dataset_id.startswith("TU_") or table_id.startswith("TU_"):
                        print("\nAdvertencia: Los valores de configuración de BigQuery en 'config/config.ini' parecen ser los predeterminados.")
                        print("Por favor, actualiza 'config/config.ini' con tus valores reales para cargar a BigQuery.")
                        print("La carga a BigQuery será omitida.")
                    else:
                        bigquery_handler.load_df_to_bigquery(processed_df, project_id, dataset_id, table_id)
                else:
                    print("\nAdvertencia: Falta información de BigQuery en 'config/config.ini' (project_id, dataset_id, o table_id).")
                    print("La carga a BigQuery será omitida.")

            except (KeyError, configparser.NoSectionError):
                print("\nError: La sección [bigquery] o alguna de sus claves no se encuentra en 'config/config.ini'.")
                print("La carga a BigQuery será omitida.")
            except Exception as e:
                print(f"\nOcurrió un error inesperado al intentar leer/usar la configuración de BigQuery: {e}")
                print("La carga a BigQuery será omitida.")

        else:
            print("\nEl procesamiento con Pandas no generó resultados o falló.")
    else:
        print("\nNo se extrajeron noticias o el scraping falló, no se realizará el post-procesamiento ni la carga a BigQuery.")

    print("\nScript principal finalizado.")