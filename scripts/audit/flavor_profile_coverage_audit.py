import sqlite3
import csv
import json
import hashlib
from pathlib import Path

def get_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest().upper()

def main():
    root_dir = Path(__file__).resolve().parent.parent.parent
    db_path = root_dir / "output" / "import" / "production.db"
    reports_dir = root_dir / "output" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    hash_before = get_hash(db_path)
    
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    
    # General counts
    cur.execute("SELECT COUNT(*) FROM whiskies")
    total_whiskies = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM flavor_profiles")
    total_flavor_profiles = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM flavor_profiles WHERE whisky_id IS NOT NULL")
    distinct_whiskies_with_fp = cur.fetchone()[0]
    whiskies_without_fp = total_whiskies - distinct_whiskies_with_fp
    
    cur.execute("SELECT COUNT(*) FROM tasting_notes")
    total_tasting_notes = cur.fetchone()[0]
    
    cur.execute('''
        SELECT COUNT(DISTINCT t.whisky_id) 
        FROM tasting_notes t
        LEFT JOIN flavor_profiles f ON t.whisky_id = f.whisky_id
        WHERE f.whisky_id IS NULL AND t.whisky_id IS NOT NULL
    ''')
    whiskies_with_tn_no_fp = cur.fetchone()[0]
    
    # Summary CSV
    with open(reports_dir / "320_17a_flavor_profile_coverage_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Metric", "Count"])
        w.writerow(["total_whiskies", total_whiskies])
        w.writerow(["total_flavor_profiles", total_flavor_profiles])
        w.writerow(["distinct_whiskies_with_flavor_profile", distinct_whiskies_with_fp])
        w.writerow(["whiskies_without_flavor_profile", whiskies_without_fp])
        w.writerow(["total_tasting_notes", total_tasting_notes])
        w.writerow(["whiskies_with_tasting_notes_but_no_flavor_profile", whiskies_with_tn_no_fp])
        
    # Missing Profiles
    cur.execute('''
        SELECT w.whisky_id, w.name, w.type, w.region, w.country, w.age_statement
        FROM whiskies w
        LEFT JOIN flavor_profiles f ON w.whisky_id = f.whisky_id
        WHERE f.whisky_id IS NULL
    ''')
    missing_profiles = cur.fetchall()
    with open(reports_dir / "321_17a_missing_flavor_profiles.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["whisky_id", "name", "type", "region", "country", "age_statement"])
        w.writerows(missing_profiles)
        
    # Missing Profiles with Tasting Notes
    cur.execute('''
        SELECT w.whisky_id, w.name, t.source_name, w.type, w.region
        FROM whiskies w
        JOIN tasting_notes t ON w.whisky_id = t.whisky_id
        LEFT JOIN flavor_profiles f ON w.whisky_id = f.whisky_id
        WHERE f.whisky_id IS NULL
        GROUP BY w.whisky_id
        ORDER BY w.whisky_id
    ''')
    missing_tn = cur.fetchall()
    with open(reports_dir / "322_17a_missing_profiles_with_tasting_notes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["whisky_id", "name", "source_name", "type", "region"])
        w.writerows(missing_tn)
        
    # Coverage by Region/Type
    cur.execute('''
        SELECT 
            IFNULL(region, 'UNKNOWN') as region, 
            IFNULL(type, 'UNKNOWN') as type,
            COUNT(*) as total,
            SUM(CASE WHEN f.whisky_id IS NOT NULL THEN 1 ELSE 0 END) as with_profile
        FROM whiskies w
        LEFT JOIN (SELECT DISTINCT whisky_id FROM flavor_profiles) f ON w.whisky_id = f.whisky_id
        GROUP BY region, type
        ORDER BY region, type
    ''')
    coverage = cur.fetchall()
    with open(reports_dir / "323_17a_coverage_by_region_type.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["region", "type", "total", "with_profile", "coverage_percent"])
        weakest = []
        for r in coverage:
            pct = round((r[3]/r[2]*100) if r[2] > 0 else 0, 2)
            w.writerow([r[0], r[1], r[2], r[3], pct])
            if r[2] >= 10:
                weakest.append((r[0], r[1], r[2], pct))
    weakest.sort(key=lambda x: x[3])
                
    # Quality Issues
    issues = []
    # Missing FK
    cur.execute("SELECT rowid, whisky_id FROM flavor_profiles WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)")
    for r in cur.fetchall():
        issues.append(["flavor_profiles", r[0], "MISSING_FK", f"whisky_id {r[1]} not in whiskies"])
        
    # Duplicates by whisky_id + flavor_source
    cur.execute('''
        SELECT whisky_id, flavor_source, COUNT(*) 
        FROM flavor_profiles 
        GROUP BY whisky_id, flavor_source 
        HAVING COUNT(*) > 1
    ''')
    for r in cur.fetchall():
        issues.append(["flavor_profiles", r[0], "DUPLICATE", f"Source {r[1]} has {r[2]} profiles for whisky {r[0]}"])
        
    # Null vectors
    cur.execute("SELECT rowid, whisky_id FROM flavor_profiles WHERE flavor_vector IS NULL OR flavor_profile IS NULL")
    for r in cur.fetchall():
        issues.append(["flavor_profiles", r[0], "NULL_DATA", "flavor_vector or flavor_profile is null"])
        
    with open(reports_dir / "324_17a_flavor_profile_quality_issues.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["table", "row_or_id", "issue_type", "description"])
        w.writerows(issues)
        
    # Generate Markdown Report
    pct_coverage = round((distinct_whiskies_with_fp / total_whiskies * 100) if total_whiskies > 0 else 0, 2)
    
    md = f"""# 17A Flavor Profile Coverage Audit Report

## DB Check
- **SHA256 Before:** `{hash_before}`
- **SHA256 After:** `{get_hash(db_path)}` (Must match)

## Summary Counts
- **Total Whiskies:** {total_whiskies}
- **Total Flavor Profiles:** {total_flavor_profiles}
- **Distinct Whiskies with Profile:** {distinct_whiskies_with_fp}
- **Whiskies WITHOUT Profile:** {whiskies_without_fp}
- **Coverage:** {pct_coverage}%
- **Whiskies with Tasting Notes but NO Profile:** {whiskies_with_tn_no_fp}

## Weakest Segments (Min 10 whiskies)
"""
    for w in weakest[:5]:
        md += f"- **Region:** {w[0]}, **Type:** {w[1]} (Total: {w[2]}, Coverage: {w[3]}%)\n"

    md += """
## High Priority Profile Candidates (Top 25)
*These whiskies have existing tasting notes but lack a flavor profile.*
"""
    for i, t in enumerate(missing_tn[:25]):
        md += f"- [{t[0]}] {t[1]} ({t[3]}, {t[4]})\n"

    md += f"""
## Quality Issues Detected
- **Total Issues:** {len(issues)}
"""
    if len(issues) == 0:
        md += "- No major quality issues found (FK missing, Duplicates, Nulls).\n"
    else:
        for iss in issues[:10]:
            md += f"- {iss[2]}: {iss[3]}\n"

    md += """
## Recommended Next Steps (17B)
- **Action:** Dry-run flavor profile candidate generation (17B).
- **Scope:** Target the whiskies that have tasting notes in `tasting_notes` and `staging_tasting_notes` but no profile.
- **Constraints:** Generate only from already trusted/high-confidence sources to preserve quality. No DB writes until manually approved.
"""

    with open(reports_dir / "325_17a_flavor_profile_coverage_audit_report.md", "w", encoding="utf-8") as f:
        f.write(md)

    with open(reports_dir / "326_17a_flavor_profile_coverage_audit_gate.txt", "w", encoding="utf-8") as f:
        f.write("GO")

if __name__ == "__main__":
    main()
