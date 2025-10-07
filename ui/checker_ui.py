import sys
import os
import json
import pandas as pd
import streamlit as st

# --- Path setup to import engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.report_generator import generate_report  # your engine function

# --- Helper function to normalize column names ---
def normalize_col(name):
    return name.strip().lower().replace(" ", "")

# --- Load default rules from JSON file ---
DEFAULT_RULES_FILE = "config/default_rules.json"
if os.path.exists(DEFAULT_RULES_FILE):
    with open(DEFAULT_RULES_FILE) as f:
        DEFAULT_RULES = json.load(f)
else:
    DEFAULT_RULES = {}

# --- Streamlit UI ---
st.title("🧾 Customer Data Mapping & Validation Tool")
st.write("Upload customer CSV files and define validation rules per customer.")

# --- Customer selection ---
customer_name = st.text_input("Enter Customer Name")

# --- Upload CSV file ---
uploaded_file = st.file_uploader("Upload customer standard file (.csv)", type=["csv"])

if uploaded_file and customer_name:
    # Read CSV file and normalize columns
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()
    st.subheader("📄 Sample of Uploaded File")
    st.dataframe(df.head())

    # --- Load or initialize rules ---
    rules_file_path = f"config/rules_{customer_name}.json"
    if os.path.exists(rules_file_path):
        with open(rules_file_path) as f:
            rules = json.load(f)
    else:
        rules = {}
        for col in df.columns:
            clean_col = col.strip()
            if clean_col in DEFAULT_RULES:
                rules[clean_col] = DEFAULT_RULES[clean_col].copy()
            else:
                rules[clean_col] = {"type": "string", "mandatory": True, "max_length": 50}

    # --- Create normalized mappings ---
    normalized_csv_cols = {normalize_col(c): c for c in df.columns}
    normalized_rules = {normalize_col(k): k for k in rules.keys()}

    # --- Prepare editable DataFrame for UI ---
    rules_list = []
    for rule_key, rule in rules.items():
        if rule["type"] == "string":
            value = str(rule.get("max_length", 50))
        elif rule["type"] == "date":
            value = rule.get("format", "%Y%m%d")
        else:
            value = ""
        rules_list.append({
            "Field Name": rule_key,
            "Type": rule.get("type", "string"),
            "Mandatory": rule.get("mandatory", True),
            "Max Length": value
        })

    rules_df = pd.DataFrame(rules_list)

    # --- Editable rules table ---
    st.subheader("⚙️ Edit Validation Rules (Table View)")
    type_options = ["string", "int", "float", "date"]

    edited_rules_df = st.data_editor(
        rules_df,
        column_config={
            "Type": st.column_config.SelectboxColumn("Type", options=type_options),
            "Mandatory": st.column_config.CheckboxColumn("Mandatory"),
            "Max Length": st.column_config.TextColumn("Max Length")
        },
        num_rows="dynamic",
        key="rules_editor"
    )

    # --- Convert back to dictionary ---
    rules = {}
    for _, row in edited_rules_df.iterrows():
        field = row["Field Name"].strip()
        rules[field] = {
            "type": row["Type"],
            "mandatory": row["Mandatory"]
        }

        if row["Type"] == "string":
            val = row["Max Length"]
            if val and str(val).isdigit():
                rules[field]["max_length"] = int(val)
            else:
                st.warning(f"⚠️ Max length for '{field}' missing or invalid, using default 50.")
                rules[field]["max_length"] = 50

        elif row["Type"] == "date":
            rules[field]["format"] = row["Max Length"] if row["Max Length"] else "%Y%m%d"

    # --- Save Rules ---
    if st.button("💾 Save Customer Rules"):
        os.makedirs("config", exist_ok=True)
        with open(rules_file_path, "w") as f:
            json.dump(rules, f, indent=2)
        st.success(f"✅ Rules saved for customer: {customer_name}")

    # --- Validate File ---
    if st.button("✅ Validate File"):
        errors = {
            "missing_columns": [],
            "extra_columns": [],
            "type_errors": [],
            "length_errors": [],
            "date_format_errors": [],
            "mandatory_errors": []
        }

        # Validation logic
        for rule_key, rule in rules.items():
            norm_rule_key = normalize_col(rule_key)
            if norm_rule_key not in normalized_csv_cols:
                errors["missing_columns"].append(rule_key)
            else:
                col = normalized_csv_cols[norm_rule_key]
                for i, val in enumerate(df[col]):
                    # --- Mandatory check ---
                    if rule.get("mandatory", False):
                        if pd.isna(val) or str(val).strip() == "":
                            errors["mandatory_errors"].append({
                                "column": rule_key,
                                "row": i + 1,
                                "value": val
                            })
                            continue

                    # --- Type checks ---
                    try:
                        if rule["type"] == "int":
                            int(val)
                        elif rule["type"] == "float":
                            float(val)
                        elif rule["type"] == "date":
                            fmt = rule.get("format", "%Y%m%d")
                            pd.to_datetime(val, format=fmt)
                    except Exception:
                        errors["type_errors"].append({"column": rule_key, "row": i + 1, "value": val})

                    # --- Length checks ---
                    if rule["type"] == "string" and "max_length" in rule:
                        if len(str(val)) > rule["max_length"]:
                            errors["length_errors"].append({
                                "column": rule_key,
                                "row": i + 1,
                                "value": val,
                                "max_length": rule["max_length"]
                            })

        # Extra columns
        extra_cols = [c for c in df.columns if normalize_col(c) not in normalized_rules]
        errors["extra_columns"] = extra_cols

        # Generate report (no type_mismatches)
        report = generate_report(errors)

        st.subheader("🧩 Validation Report")
        st.json(report)

        if not any(errors.values()):
            st.success("✅ File passes all validation rules!")
        else:
            st.warning("⚠️ File does NOT pass validation rules!")
