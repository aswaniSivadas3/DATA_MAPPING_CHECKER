import copy
import streamlit as st
import xml.etree.ElementTree as ET
from io import BytesIO
from utils.file_io import load_json, save_json, read_csv
from utils.rules import init_rules, prepare_rules_df, df_to_rules_dict
from utils.validation import validate_file
from engine.report_generator import generate_report
from engine.derived_rules import apply_derived_rules
import json
import os
import pandas as pd
import oracledb

def run_checker_ui():
    # Load default rules
    DEFAULT_RULES = load_json("config/default_rules.json", default={})

    st.title("🧾 Customer Data Mapping & Validation Tool")
    st.write("Upload customer CSV files and define validation & derived rules per customer.")

    # Customer selection
    customer_name = st.text_input("Enter Customer Name")
    file_category = st.selectbox(
        "Select File Category",
        options=["Customer", "Item", "Contacts", "Users"]
    )
    #uploaded_file = st.file_uploader("Upload standard CSV file (.csv)", type=["csv"])
    uploaded_file_category = st.selectbox(
        "Select File type",
        options=["csv","json","txt","xml"]
    )

 
    if uploaded_file_category == "csv":
        try:
            uploaded_file = st.file_uploader("Upload standard file (.csv)", type=["csv"])
            df = read_csv(uploaded_file).fillna("")
        except:
            print('Error catched')
    elif uploaded_file_category == "json":
        try:
            uploaded_file = st.file_uploader("Upload customer standard file (.json)", type=["json"])
            df = pd.read_json(uploaded_file)
            df.to_csv('csvfile.csv', encoding='utf-8', index=False)
        except:
            print('Error catched')
    elif uploaded_file_category == "xml":
        try:
            uploaded_file = st.file_uploader("Upload customer standard file (.xml)", type=["xml"])
            df = pd.read_xml(uploaded_file)
            df.to_csv('csvfile.csv', encoding='utf-8', index=False)
        except:
            print('Error catched')
    else:
        try:
            uploaded_file = st.file_uploader("Upload standard file (.csv)", type=["csv"])
            df = read_csv(uploaded_file).fillna("")
        except:
            print('Error catched')
    # File category - END
 

    if uploaded_file and customer_name:
        # Read CSV and replace NaN
        #df = read_csv(uploaded_file).fillna("")
        st.subheader("📄 Sample of Uploaded File")
        st.dataframe(df.head())

        # Load saved rules or initialize defaults
        rules_file_path = f"config/rules_{file_category.lower()}_{customer_name}.json"
        saved_rules = load_json(rules_file_path, default=None)
        rules = saved_rules if saved_rules else init_rules(df.columns, DEFAULT_RULES)
        original_rules = copy.deepcopy(rules)

        # Prepare editable rules table
        rules_df = prepare_rules_df(rules)
        type_options = ["string", "int", "float", "date"]

        st.subheader("⚙️ Edit Validation & Derived Rules")
        edited_rules_df = st.data_editor(
            rules_df,
            column_config={
                "Type": st.column_config.SelectboxColumn("Type", options=type_options),
                "Mandatory": st.column_config.CheckboxColumn("Mandatory"),
                "Max Length": st.column_config.TextColumn("Max Length"),
                "Derived Rule": st.column_config.TextColumn("Derived Rule")
            },
            num_rows="dynamic",
            key="rules_editor"
        )

        # Convert table edits back to rules dict
        rules = df_to_rules_dict(edited_rules_df, existing_rules=rules)

        # Save rules button
        if st.button("💾 Save Customer Rules"):
            save_json(rules_file_path, rules)
            st.success(f"✅ Rules saved for customer: {customer_name}")

        # Validate file button
        if st.button("✅ Validate File"):
            try:
                # Apply derived rules
                df_transformed = apply_derived_rules(df.copy(), rules)
                st.info("📘 Derived logic applied. Preview:")
                st.dataframe(df_transformed.head())

                # Validate
                errors = validate_file(df_transformed, rules)
                report = generate_report(errors)
                st.subheader("🧩 Validation Report")
                st.json(report)

                # Flag indicating validation passed
                validation_passed = not any(errors.values())

                if validation_passed:
                    st.success("✅ File passes all validation rules!")
                    st.session_state.button_clicked = False
                    # Show Load Data button
                    if st.button("Load Data") or True:
                    #st.button("Load Data")
                        st.session_state.button_clicked = True
                        # Show Load Data button
                        #st.write("Button was clicked!")
                        try:
                                
                                # --- Load JSON payload ---
                                with open("config/insert_payload_db_ready.json", "r") as f:
                                    payload = json.load(f)
    
                                    table_name = payload["table"]
                                    rows = payload["rows"]
                                    
                                    # --- Oracle Connection ---
                                    conn = oracledb.connect(
                                        user="STN_TEST_DBA",
                                        password="sidetrade",
                                        dsn="192.168.31.115:1521/ORCPRV08"
                                    )
                                    cur = conn.cursor()
                                    
                                    # --- Retrieve valid columns from DB ---
                                    cur.execute("""
                                        SELECT COLUMN_NAME
                                        FROM ALL_TAB_COLUMNS
                                        WHERE TABLE_NAME = :tbl
                                    """, {"tbl": table_name.upper()})
                                    valid_columns = {r[0] for r in cur.fetchall()}
                                    
                                    # --- Prepare and execute inserts ---
                                    for row in rows:
                                        # Filter only valid DB columns
                                        cols = [col for col in row.keys() if col.upper() in valid_columns]
                                        if not cols:
                                            print(f"Skipping row, no valid columns: {row}")
                                            continue
                                    
                                        placeholders = ", ".join([f":{i+1}" for i in range(len(cols))])
                                        sql = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})"
                                        values = [row[c] for c in cols]
                                    
                                        try:
                                            cur.execute(sql, values)
                                            print(f"Inserted: {cols}")
                                        except Exception as e:
                                            print(f"Failed to insert row: {e}")
                                    
                                    # --- Commit and close ---
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                
                        except Exception as e:
                                st.error(f"❌ Error loading data: {str(e)}")
                else:
                   st.warning("⚠️ File does NOT pass validation rules!")

            except Exception as e:
                st.error(f"❌ Error validating file: {str(e)}")
