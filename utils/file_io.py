import json
import os
import pandas as pd

def load_json(path, default=None):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def read_csv(file):
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()
    return df
