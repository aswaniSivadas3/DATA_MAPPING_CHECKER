import pandas as pd

def apply_derived_rules(df, rules):
    """
    Apply derived rules safely to the DataFrame.
    All columns in the formula are cast to string for concatenation.
    """
    for field, rule in rules.items():
        if "derived" in rule:
            formula = rule["derived"]
            expr = formula

            # Replace column names with df['col'].astype(str) for string concatenation
            for col in df.columns:
                if col in expr:
                    expr = expr.replace(col, f"df['{col}'].astype(str)")

            try:
                # Use Python eval with only df and pd
                df[field] = eval(expr, {"df": df, "pd": pd})
            except Exception as e:
                raise ValueError(f"❌ Error computing derived rule for '{field}': {e}")

    return df
