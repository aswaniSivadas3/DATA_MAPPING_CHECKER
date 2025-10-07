def compare_schema(df, standard_schema):
    client_columns = set(df.columns)
    standard_columns = set(standard_schema.keys())

    matching = client_columns & standard_columns
    missing = standard_columns - client_columns
    extra = client_columns - standard_columns

    report = {
        "matching_columns": sorted(list(matching)),
        "missing_columns": sorted(list(missing)),
        "extra_columns": sorted(list(extra))
    }
    return report


def infer_type(series):
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"
    return "string"

def compare_types(df, standard_schema):
    mismatches = []
    for col, expected_type in standard_schema.items():
        if col not in df.columns:
            continue  # skip missing columns
        actual_type = infer_type(df[col])
        if actual_type != expected_type:
            mismatches.append({
                "column": col,
                "expected": expected_type,
                "found": actual_type
            })
    return mismatches