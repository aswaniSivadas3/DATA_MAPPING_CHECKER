import pandas as pd
from utils.normalization import normalize_col

def init_rules(df_columns, default_rules):
    """Initialize rules for CSV columns using default rules if available."""
    normalized_defaults = {normalize_col(k): v for k, v in default_rules.items()}
    rules = {}
    for col in df_columns:
        norm_col = normalize_col(col)
        if norm_col in normalized_defaults:
            rules[col] = normalized_defaults[norm_col].copy()
        else:
            rules[col] = {"type": "string", "mandatory": True, "max_length": 50}
    return rules

def prepare_rules_df(rules):
    """Prepare editable DataFrame for Streamlit UI."""
    rules_list = []
    for col, rule in rules.items():
        if rule["type"] == "string":
            max_len = str(rule.get("max_length", 50))
        else:
            max_len = ""
        derived = rule.get("derived", "")
        rules_list.append({
            "Field Name": col,
            "Type": rule.get("type", "string"),
            "Mandatory": rule.get("mandatory", True),
            "Max Length": max_len,
            "Derived Rule": derived
        })
    return pd.DataFrame(rules_list)

def df_to_rules_dict(df, existing_rules=None):
    """
    Convert DataFrame back to rules dict.
    Preserves derived rules and updates validation settings.
    """
    rules = existing_rules.copy() if existing_rules else {}
    for _, row in df.iterrows():
        field = row["Field Name"].strip()
        if field not in rules:
            rules[field] = {}
        rules[field]["type"] = row["Type"]
        rules[field]["mandatory"] = row["Mandatory"]
        if row["Type"] == "string":
            rules[field]["max_length"] = int(row["Max Length"]) if str(row["Max Length"]).isdigit() else 50
        elif row["Type"] == "date":
            rules[field]["format"] = row.get("Max Length") or "%Y%m%d"

        # Handle derived rule
        if row.get("Derived Rule", "").strip():
            rules[field]["derived"] = row["Derived Rule"].strip()
        elif "derived" in rules[field]:
            # remove if user cleared it
            del rules[field]["derived"]
    return rules
