from engine.file_loader import load_file
from engine.schema_comparator import compare_schema, compare_types
from engine.report_generator import generate_report
import json, sys

def main(client_file, schema_file):
    df = load_file(client_file)
    with open(schema_file) as f:
        sidetrade_schema = json.load(f)

    schema_report = compare_schema(df, sidetrade_schema)
    type_mismatches = compare_types(df, sidetrade_schema)
    report = generate_report(schema_report, type_mismatches)

    print(json.dumps(report, indent=2))
    if report["is_standard"]:
        print("✅ Client file matches Sidetrade standard format.")
    else:
        print("⚠️ Client file differs from Sidetrade format.")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
