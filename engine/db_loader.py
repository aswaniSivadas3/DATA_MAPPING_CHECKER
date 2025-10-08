
import pandas as pd
from sqlalchemy import create_engine
import json
import os

def load_to_oracle(df, customer_name, mapping_file="config/column_mapping.json", db_config_file="config/db_config.json"):
    
    try:
        # --- Load DB connection details ---
        with open(db_config_file) as f:
            db_conf = json.load(f)

        username = db_conf["username"]
        password = db_conf["password"]
        dsn = db_conf["dsn"]

        # --- Create engine ---
        engine = create_engine(f"oracle+oracledb://{username}:{password}@{dsn}")

        # --- Apply column mapping if provided ---
        if mapping_file and os.path.exists(mapping_file):
            with open(mapping_file) as f:
                col_map = json.load(f)
            df.rename(columns=col_map, inplace=True)
        else:
            print("⚠️ No mapping file found — using CSV column names as-is.")

        # --- Define target table ---
        table_name = f"{customer_name.upper()}_DATA"

        # --- Write data to Oracle ---
        df.to_sql(
            name=table_name,
            con=engine,
            index=False,
            if_exists="append",  # or "replace"
            chunksize=500,
            method="multi"
        )

        return f"✅ Data successfully loaded into Oracle table: {table_name}"

    except Exception as e:
        return f"❌ Failed to load data: {e}"
