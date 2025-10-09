import pandas as pd
from utils.normalization import normalize_col

def validate_file(df, rules):
    """
    Validate DataFrame against rules (supports string/int/float/date).
    Handles mandatory, type, length, and date format checks.
    Derived columns are assumed to already be computed.
    """
    normalized_csv_cols = {normalize_col(c): c for c in df.columns}
    normalized_rules = {normalize_col(k): k for k in rules.keys()}

    errors = {
        "missing_columns": [],
        "extra_columns": [],
        "type_errors": [],
        "length_errors": [],
        "date_format_errors": [],
        "mandatory_errors": []
    }

    for rule_key, rule in rules.items():
        norm_rule_key = normalize_col(rule_key)
        if norm_rule_key not in normalized_csv_cols:
            errors["missing_columns"].append(rule_key)
            continue

        col = normalized_csv_cols[norm_rule_key]
        col_type = rule.get("type", "string")

        for i, val in enumerate(df[col]):
            val_str = str(val).strip() if val is not None else ""

            # --- Mandatory check
            if rule.get("mandatory", False) and val_str == "":
                errors["mandatory_errors"].append({
                    "column": rule_key,
                    "row": i + 1,
                    "value": val
                })
                continue

            # Skip empty optional fields
            if val_str == "":
                continue

            # --- Type validation
            try:
                if col_type == "int":
                    int(val)
                elif col_type == "float":
                    float(val)
                elif col_type == "date":
                    # Expecting YYYYMMDD
                    pd.to_datetime(val, format="%Y%m%d")
            except Exception:
                if col_type == "date":
                    errors["date_format_errors"].append({
                        "column": rule_key,
                        "row": i + 1,
                        "value": val,
                        "expected_format": "YYYYMMDD"
                    })
                else:
                    errors["type_errors"].append({
                        "column": rule_key,
                        "row": i + 1,
                        "value": val
                    })
                continue

            # --- Max length check
            if col_type == "string" and "max_length" in rule:
                if len(val_str) > int(rule["max_length"]):
                    errors["length_errors"].append({
                        "column": rule_key,
                        "row": i + 1,
                        "value": val,
                        "max_length": rule["max_length"]
                    })

    # --- Extra columns
    errors["extra_columns"] = [
        c for c in df.columns if normalize_col(c) not in normalized_rules
    ]

    return errors
