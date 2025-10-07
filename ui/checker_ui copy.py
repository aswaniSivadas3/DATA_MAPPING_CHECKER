import sys
import os
import json

# 2. Third-party imports
import pandas as pd
import streamlit as st

# 3. Adjust Python path so engine modules are found
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 4. Import your engine modules AFTER path adjustment
from engine.file_loader import load_file
from engine.schema_comparator import compare_schema, compare_types
from engine.report_generator import generate_report

st.title("Sidetrade Interface Checker")

uploaded_file = st.file_uploader("Upload client file", type=["csv","txt"])
schema_file = st.file_uploader("Upload Sidetrade schema", type=["json"])

if uploaded_file and schema_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(".txt") else pd.read_csv(uploaded_file)
    sidetrade_schema = json.load(schema_file)
    
    schema_report = compare_schema(df, sidetrade_schema)
    type_mismatches = compare_types(df, sidetrade_schema)
    
    st.subheader("Results")
    st.json({
        "Matching Columns": schema_report["matching_columns"],
        "Missing Columns": schema_report["missing_columns"],
        "Extra Columns": schema_report["extra_columns"],
        "Type Mismatches": type_mismatches
    })
    
    if not schema_report["missing_columns"] and not schema_report["extra_columns"] and not type_mismatches:
        st.success("✅ Client file matches the default Sidetrade format.")
    else:
        st.warning("⚠️ Custom mapping required.")
