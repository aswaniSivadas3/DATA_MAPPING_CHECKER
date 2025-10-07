import json

def generate_report(schema_report, output_path="report.json"):
    """Generate a structured validation report without type_mismatches."""
    # Determine if file passes validation
    is_standard = (
        not schema_report.get("missing_columns") and
        not schema_report.get("extra_columns") and
        not schema_report.get("type_errors") and
        not schema_report.get("length_errors") and
        not schema_report.get("date_format_errors") and
        not schema_report.get("mandatory_errors")
    )

    # Build report dictionary
    report = {
        "column_comparison": schema_report,
        "is_standard": is_standard
    }

    # Optional: clean out empty sections for readability
    report["column_comparison"] = {k: v for k, v in schema_report.items() if v}

    # Save to JSON file
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report
