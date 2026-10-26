import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
import pandas as pd

# Load environment variables from .env
load_dotenv()

def get_db_engine():
    user = urllib.parse.quote_plus(os.getenv('POSTGRES_USER', 'postgres'))
    password = urllib.parse.quote_plus(os.getenv('POSTGRES_PASSWORD', ''))
    host = urllib.parse.quote_plus(os.getenv('POSTGRES_HOST', 'localhost'))
    port = urllib.parse.quote_plus(os.getenv('POSTGRES_PORT', '5432'))
    dbname = urllib.parse.quote_plus(os.getenv('POSTGRES_DATABASE', 'olist_warehouse'))

    # connection string
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)

def main():
    engine = get_db_engine()

    # Mapping nama file CSV ke nama tabel di Postgres
    files_to_load = {
        "olist_orders_dataset.csv": "orders",
        "olist_customers_dataset.csv": "customers",
        "olist_products_dataset.csv": "products",
        "olist_order_items_dataset.csv": "order_items"
    }

    print("Start olist ingestion data process")
    
    for csv_file, table_name in files_to_load.items():
        file_path = f"data/{csv_file}"
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}. Please make sure it exists.")
            continue

        print(f"⏳ Process {csv_file}...")
        df = pd.read_csv(file_path)

        print(f"⬆️  Uploading {len(df)} rows to raw.{table_name}...")

        with engine.begin() as conn:
            conn.execute(text(f"""
                DO $$
                BEGIN
                    IF to_regclass('raw.{table_name}') IS NOT NULL THEN
                        EXECUTE 'TRUNCATE TABLE raw.{table_name} CASCADE';
                    END IF;
                END $$;
            """))

        # Inserting into raw schema, replace table if it already exists (for development phase)
        df.to_sql(
            name=table_name,
            con=engine,
            schema="raw",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000
        )
        print(f"✅ Success loading raw.{table_name}")

    print("🎉 Done!")

if __name__ == "__main__":
    main()