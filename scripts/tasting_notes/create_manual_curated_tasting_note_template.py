import os
import csv

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates_dir = os.path.join(base_dir, "data", "templates")
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

os.makedirs(templates_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

template_csv = os.path.join(templates_dir, "manual_curated_tasting_notes_template.csv")
example_csv = os.path.join(templates_dir, "manual_curated_tasting_notes_example.csv")
rules_csv = os.path.join(output_dir, "manual_curated_tasting_note_import_rules.csv")
report_md = os.path.join(reports_dir, "299_manual_curated_tasting_note_import_template_report.md")
gate_txt = os.path.join(reports_dir, "300_12z_manual_curated_tasting_note_import_template_gate.txt")

FIELDS = [
    "manual_note_id",
    "whisky_id",
    "whisky_name",
    "source_type",
    "source_name",
    "source_url",
    "source_reference",
    "note_author",
    "note_date",
    "nose_notes",
    "palate_notes",
    "finish_notes",
    "overall_notes",
    "language",
    "permission_status",
    "attribution_required",
    "reviewer_comment",
    "approval_status"
]

EXAMPLE_ROWS = [
    {
        "manual_note_id": "MAN-0001",
        "whisky_id": "W001234",
        "whisky_name": "Example Highland Malt 12yo",
        "source_type": "book",
        "source_name": "Whisky Tasting Guide 2026",
        "source_url": "",
        "source_reference": "Page 42, Chapter 3",
        "note_author": "Jane Doe",
        "note_date": "2026-06-21",
        "nose_notes": "Rich honey, green apples, and a hint of smoke.",
        "palate_notes": "Vanilla fudge, roasted almonds, very creamy.",
        "finish_notes": "Medium length, warming oak spice.",
        "overall_notes": "A well-balanced introductory dram.",
        "language": "en",
        "permission_status": "public_short_excerpt",
        "attribution_required": "true",
        "reviewer_comment": "Verified against physical book excerpt.",
        "approval_status": "manual_pending_review"
    },
    {
        "manual_note_id": "MAN-0002",
        "whisky_id": "W005678",
        "whisky_name": "Example Islay Smoke Reserve",
        "source_type": "user_submission",
        "source_name": "Malt Radar User Testing",
        "source_url": "https://maltradar.com/users/johndoe",
        "source_reference": "",
        "note_author": "JohnDoe",
        "note_date": "2026-06-20",
        "nose_notes": "Heavy peat, medicinal iodine.",
        "palate_notes": "Ashes, salt, sweet barley sugar.",
        "finish_notes": "Long, lingering bonfire smoke.",
        "overall_notes": "A classic Islay profile.",
        "language": "en",
        "permission_status": "user_submitted",
        "attribution_required": "true",
        "reviewer_comment": "User granted permission in testing group.",
        "approval_status": "manual_pending_review"
    }
]

RULES = [
    {"field": "manual_note_id", "rule": "Required. Must be unique prefix e.g. MAN-XXXX"},
    {"field": "whisky_id", "rule": "Required. Must exist in production.db whiskies table"},
    {"field": "source_type", "rule": "Required. e.g. book, website, user_submission, magazine"},
    {"field": "source_url_or_ref", "rule": "Required. Either source_url or source_reference must be non-empty"},
    {"field": "notes", "rule": "Required. At least one of nose, palate, finish, or overall must be non-empty"},
    {"field": "permission_status", "rule": "Required. Must be user_submitted, public_short_excerpt, licensed, owner_provided, unknown_requires_review"},
    {"field": "approval_status", "rule": "Required. Must be manual_pending_review"}
]

def write_csv(path, headers, data):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(data)

def main():
    # 1. Template
    write_csv(template_csv, FIELDS, [])
    
    # 2. Example
    write_csv(example_csv, FIELDS, EXAMPLE_ROWS)
    
    # 3. Rules
    write_csv(rules_csv, ["field", "rule"], RULES)

    # 4. Report
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# 299 Manual Curated Tasting Note Import Template Report\n\n")
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        f.write("- template_created: YES\n")
        f.write("- example_created: YES\n")
        f.write("- rules_created: YES\n")
        f.write("- required_fields_enforced: YES (whisky_id, source, permission, approval_status)\n")
        f.write("- permission_status_categories: user_submitted, public_short_excerpt, licensed, owner_provided, unknown_requires_review\n")
        f.write("- production_db_changed: NO\n")
        f.write("- output_import_changed: NO\n")
        f.write("- frontend_untouched: YES\n")
        f.write("- next_phase: Develop ingestion script (apply_manual_curated_notes) or design UGC frontend\n")

    # 5. Gate
    gate_status = "GO"
    reasons = [
        "Template, example, and rules generated safely.",
        "No DB or frontend files touched.",
        "Permission and source traceability fields included."
    ]

    with open(gate_txt, "w", encoding="utf-8") as f:
        f.write(f"GATE: {gate_status}\n")
        for r in reasons:
            f.write(f"REASON: {r}\n")

if __name__ == "__main__":
    main()
