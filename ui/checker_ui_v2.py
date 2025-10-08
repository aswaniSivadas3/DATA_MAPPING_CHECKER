import sys
import os
import json
import pandas as pd
import streamlit as st

# --- Add project root to sys.path to import 'engine' module ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Imports from engine ---
from engine.report_generator import generate_report
from engine.db_loader import load_to_oracle

# --- Helper function to normalize column names ---
def normalize_col(name):
    return name.strip().lower().replace(" ", "")

# --- Load default rules ---
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
            clean_col_lower = clean_col.lower().replace(" ", "")
            if clean_col_lower in DEFAULT_RULES:
                rules[clean_col] = DEFAULT_RULES[clean_col_lower].copy()
            else:
                rules[clean_col] = {"type": "string", "mandatory": True, "max_length": 50}

    normalized_csv_cols = {normalize_col(c): c for c in df.columns}
    normalized_rules = {normalize_col(k): k for k in rules.keys()}

    # --- Prepare rules DataFrame for editing ---
    rules_list = []
    for rule_key, rule in rules.items():
        if rule["type"] == "string":
            value = str(rule.get("max_length", 50))
        elif rule["type"] == "date":
            value = rule.get("format", "%Y%m%d")
        else:
            value = ""
        rules_list.append({
            "Field Name": str(rule_key),
            "Type": str(rule.get("type", "string")),
            "Mandatory": bool(rule.get("mandatory", True)),
            "Max Length / Format": str(value),
            "Derived Rule": ""
        })

    rules_df = pd.DataFrame(rules_list)

    # --- Ensure all columns have correct type ---
    rules_df["Field Name"] = rules_df["Field Name"].astype(str)
    rules_df["Type"] = rules_df["Type"].astype(str)
    rules_df["Mandatory"] = rules_df["Mandatory"].astype(bool)
    rules_df["Max Length / Format"] = rules_df["Max Length / Format"].astype(str)
    rules_df["Derived Rule"] = rules_df["Derived Rule"].astype(str)

    # --- Editable rules table ---
    st.subheader("⚙️ Edit Validation Rules (Table View)")
    type_options = ["string", "int", "float", "date"]

    edited_rules_df = st.data_editor(
        rules_df,
        column_config={
            "Type": st.column_config.SelectboxColumn("Type", options=type_options),
            "Mandatory": st.column_config.CheckboxColumn("Mandatory"),
            "Max Length / Format": st.column_config.TextColumn("Max Length / Format"),
            "Derived Rule": st.column_config.TextColumn("Derived Rule")
        },
        num_rows="dynamic",
        key="rules_editor"
    )

    # --- Convert edited DataFrame back to rules dict ---
    rules = {}
    for _, row in edited_rules_df.iterrows():
        field = row["Field Name"].strip()
        rules[field] = {
            "type": row["Type"],
            "mandatory": row["Mandatory"]
        }

        if row["Type"] == "string":
            val = row["Max Length / Format"]
            if val.isdigit():
                rules[field]["max_length"] = int(val)
            else:
                rules[field]["max_length"] = 50
        elif row["Type"] == "date":
            rules[field]["format"] = row["Max Length / Format"] if row["Max Length / Format"] else "%Y%m%d"

        # Add derived rule if defined
        if row["Derived Rule"].strip():
            rules[field]["derived_rule"] = row["Derived Rule"].strip()

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

        for rule_key, rule in rules.items():
            norm_rule_key = normalize_col(rule_key)
            if norm_rule_key not in normalized_csv_cols:
                errors["missing_columns"].append(rule_key)
            else:
                col = normalized_csv_cols[norm_rule_key]
                for i, val in enumerate(df[col]):
                    if rule.get("mandatory", False):
                        if pd.isna(val) or str(val).strip() == "":
                            errors["mandatory_errors"].append({"column": rule_key, "row": i + 1, "value": val})
                            continue

                    # Type checks
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

                    # Length checks
                    if rule["type"] == "string" and "max_length" in rule:
                        if len(str(val)) > rule["max_length"]:
                            errors["length_errors"].append({
                                "column": rule_key,
                                "row": i + 1,
                                "value": val,
                                "max_length": rule["max_length"]
                            })

        extra_cols = [c for c in df.columns if normalize_col(c) not in normalized_rules]
        errors["extra_columns"] = extra_cols

        # Generate report
        report = generate_report(errors)

        st.subheader("🧩 Validation Report")
        st.json(report)

        # --- If valid, allow DB load ---
        if not any(errors.values()):
            st.success("✅ File passes all validation rules!")
            # --- Apply mapping rules and show updated table ---
            if st.button("🔄 Apply Mapping Rules and Preview Data"):
            # Skip the first row (index 0)
                mapped_df = df.iloc[1:].copy()

                for rule_key, rule in rules.items():
        # Check for derived rule
                    if "derived_rule" in rule:
                        try:
                            mapped_df[rule_key] = mapped_df.eval(rule["derived_rule"])
                        except Exception as e:
                            st.error(f"Error applying derived rule for {rule_key}: {e}")

        # Rename columns if mapping rules include renaming
                    if "mapped_name" in rule:
                        mapped_df.rename(columns={rule_key: rule["mapped_name"]}, inplace=True)

                    st.subheader("📊 Data After Applying Mapping Rules (Header Skipped)")
                    st.dataframe(mapped_df.head(50))  # show first 50 rows

            if st.button("📥 Load Data to Oracle Database"):
                mapping_file = f"config/column_mapping_clients.json"
                result = load_to_oracle(df, customer_name, mapping_file, rules)
                if result.startswith("✅"):
                    st.success(result)
                else:
                    st.error(result)
        else:
            st.warning("⚠️ File does NOT pass validation rules!")
    # --- Apply mapping rules and show updated table ---

