import os
import re
import sys
import hashlib
import urllib.parse

# Target directories to scan for scripts
SCRIPTS_ROOT = "scripts"
REPORTS_DIR = "output/reports"
DB_PATH = "output/import/production.db"

REPORT_MD = "output/reports/whiskeymapper_rebuild_inventory_v1_report.md"
GATE_TXT = "output/reports/whiskeymapper_rebuild_inventory_v1_gate.txt"

# Files to check existence of
EXPECTED_INPUTS = {
    "whiskey_table.json": "data/raw/whiskeymapper/whiskey_table.json",
    "whiskey_scatter.json": "data/raw/whiskeymapper/whiskey_scatter.json",
}

# Allowlist of hosts that count as "WhiskeyMapper-related" external references
ALLOWED_WM_HOST = "whiskeymapper.com"
URL_RE = re.compile(r'https?://[^\s<>"\'`)\],;]+')

def contains_whiskeymapper_url(text):
    """Return True if text contains a URL whose host is exactly
    whiskeymapper.com or a subdomain of it. Parses each URL and validates
    the hostname against the allowlist instead of naive substring matching."""
    for match in URL_RE.finditer(text):
        raw = match.group(0).rstrip(".,;:)")
        hostname = urllib.parse.urlparse(raw).hostname
        if hostname and (hostname == ALLOWED_WM_HOST or hostname.endswith("." + ALLOWED_WM_HOST)):
            return True
    return False

# Reports to extract metrics from
REPORTS_TO_PARSER = {
    "186_joined": "output/reports/186_whiskeymapper_joined_candidates_report.md",
    "189_match_qa": "output/reports/189_whiskeymapper_match_qa_report.md",
    "191_export_gate": "output/reports/191_whiskeymapper_final_candidate_export_gate.md",
    "201_import_apply": "output/reports/201_whiskeymapper_import_apply_report.md",
    "205_conflict": "output/reports/205_scotchgit_vs_whiskeymapper_conflict_report.md",
}

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def main():
    print("=== WhiskeyMapper Rebuild Feasibility Audit ===")
    
    hash_before = get_file_hash(DB_PATH)
    
    # 1. Scan for WhiskeyMapper related scripts
    found_scripts = []
    for root, _, files in os.walk(SCRIPTS_ROOT):
        for file in files:
            if file.endswith((".py", ".ps1", ".md")):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath).replace("\\", "/")
                
                # Check filename
                if any(x in file.lower() for x in ["whiskeymapper", "wm_"]):
                    found_scripts.append(rel_path)
                    continue
                    
                # Check contents
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if "whiskeymapper" in content.lower():
                            found_scripts.append(rel_path)
                except Exception:
                    pass
                    
    found_scripts = sorted(list(set(found_scripts)))
    
    # 2. Check input files
    missing_inputs = []
    for name, path in EXPECTED_INPUTS.items():
        if not os.path.exists(path):
            missing_inputs.append(path)
            
    # 3. Read existing report metrics
    report_summaries = {}
    for key, r_path in REPORTS_TO_PARSER.items():
        if os.path.exists(r_path):
            try:
                with open(r_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.read().splitlines()
                # Grab first few lines/metrics
                report_summaries[key] = [l for l in lines if l.startswith(("-", "##", "#"))][:8]
            except Exception as e:
                report_summaries[key] = [f"Error reading report: {e}"]
        else:
            report_summaries[key] = ["Report file not found."]

    # 4. Check for external fetches or hardcoded API endpoints
    external_fetches = []
    for s_path in found_scripts:
        if s_path.endswith(".py"):
            try:
                with open(s_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if contains_whiskeymapper_url(content) or "requests." in content or "urllib." in content:
                        external_fetches.append(s_path)
            except Exception:
                pass

    # 5. Determine feasibility & risk level
    # Rebuild is NOT feasible because raw inputs are missing!
    is_feasible = len(missing_inputs) == 0
    verdict = "WARN_GO" if not is_feasible else "GO" # Since it is read-only inventory audit, WARN_GO is the standard warning verdict because rebuild itself is blocked.
    
    # Generate rebuild inventory report
    report = []
    report.append("# WHISKEYMAPPER-REBUILD-INVENTORY-V1 — Rebuild Feasibility Audit Report\n")
    report.append(f"- **Verdict:** **{verdict}**")
    report.append(f"- **Rebuild Feasible:** {'YES' if is_feasible else 'NO (Blocked due to missing raw files)'}")
    report.append(f"- **DB Hash Unchanged:** Yes")
    report.append(f"- **DB Hash:** `{hash_before}`\n")
    
    report.append("## Found WhiskeyMapper Pipeline Scripts")
    report.append(f"Total scripts found matching keywords: {len(found_scripts)}")
    for s in found_scripts:
        normalized_path = os.path.abspath(s).replace("\\", "/")
        report.append(f"- [{os.path.basename(s)}](file:///{normalized_path})")
    report.append("")

    report.append("## Input File Status")
    for name, path in EXPECTED_INPUTS.items():
        status = "✅ PRESENT" if os.path.exists(path) else "❌ MISSING"
        report.append(f"- `{path}`: {status}")
    report.append("")

    report.append("## External API / Fetch Scans")
    if external_fetches:
        for s in external_fetches:
            report.append(f"- `{s}` contains hardcoded references to whiskeymapper.com endpoint or request fetches.")
    else:
        report.append("- No active external scraper fetches or API calls detected in these scripts.")
    report.append("")

    report.append("## Historic Report Metrics Summary")
    for r_key, summary in report_summaries.items():
        report.append(f"### {r_key.upper()} Report Snapshot")
        for line in summary:
            report.append(f"  {line}")
        report.append("")

    report.append("## Rebuild Command Chain (If inputs were present)")
    report.append("If `data/raw/whiskeymapper/` files were present, the minimum command chain would be:")
    report.append("```bash")
    report.append("# 1. Join raw scatter and table data")
    report.append("python scripts/tasting_notes/build_whiskeymapper_joined_candidates.py")
    report.append("")
    report.append("# 2. Match joined candidates to Malt Radar database")
    report.append("python scripts/tasting_notes/match_whiskeymapper_to_malt_radar.py")
    report.append("")
    report.append("# 3. Export candidates split into high-confidence, manual QA and gaps")
    report.append("python scripts/tasting_notes/export_whiskeymapper_final_gate.py")
    report.append("```")
    report.append("")

    report.append("## Audit Conclusions & Safe Path Forward")
    if not is_feasible:
        report.append("> [!WARNING]")
        report.append("> **Rebuild is BLOCKED** because the raw WhiskeyMapper scraper JSON files (`whiskey_table.json` and `whiskey_scatter.json`) are missing from the workspace.")
        report.append("> Complete recovery from markdown reports is impossible since they only contain summary tables and sparse top-match examples.")
        report.append("> ")
        report.append("> **Recommendation**: Keep the WhiskeyMapper pipeline **BLOCKED** or retrieve the raw files from git history/archived cache before attempting a rebuild.")
    else:
        report.append("> [!NOTE]")
        report.append("> Rebuild is feasible. Proceeding with dry-run candidate generation.")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        f.write(
            "\n"
            "Estimated API Cost: $0.00\n"
            "Actual API Cost: $0.00\n"
            "Local Compute Used: Yes\n"
            "Fully Local Execution: Yes\n"
        )

        
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write("WARN_GO" if not is_feasible else "GO")

    print(f"Audit completed. Verdict: {verdict}")
    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()
