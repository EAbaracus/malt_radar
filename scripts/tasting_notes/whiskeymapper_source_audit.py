import os
import requests
import re
import csv
from urllib.parse import urljoin

# Setup directories
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
reports_dir = os.path.join(base_dir, "output", "reports")
data_dir = os.path.join(base_dir, "data", "output")
os.makedirs(reports_dir, exist_ok=True)
os.makedirs(data_dir, exist_ok=True)

report_file = os.path.join(reports_dir, "182_whiskeymapper_source_audit.md")
candidates_report_file = os.path.join(reports_dir, "183_whiskeymapper_candidates_report.md")
csv_file = os.path.join(data_dir, "whiskeymapper_candidates.csv")

TARGET_URL = "https://whiskeymapper.com/"
PATTERNS = [
    "api", "json", "whiskey", "whisky", "flavor", "flavour",
    "similar", "profile", "vector", "search", "bottle", "distillery"
]

def run_audit():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    audit_lines = ["# Whiskey Mapper Source Audit", ""]
    candidate_lines = ["# Candidate Endpoints & Assets", ""]
    
    candidates = []
    decision = "BLOCKED"
    status_msg = "no usable programmatic access found"

    try:
        response = requests.get(TARGET_URL, headers=headers, timeout=10)
        audit_lines.append(f"**HTTP Status:** {response.status_code}")
        audit_lines.append(f"**Content-Type:** {response.headers.get('Content-Type')}")
        audit_lines.append(f"**Content-Length:** {len(response.content)} bytes")
        audit_lines.append(f"**Is Redirect:** {response.is_redirect or response.history != []}")
        audit_lines.append("")

        if response.status_code == 200:
            html_content = response.text
            
            # Simple regex to extract script src
            script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html_content)
            js_bundles = [urljoin(TARGET_URL, src) for src in script_srcs if src]
            
            audit_lines.append(f"Found {len(js_bundles)} JS bundle(s).")
            for b in js_bundles:
                audit_lines.append(f"- {b}")
                candidates.append({"type": "js_bundle", "url": b})
            
            audit_lines.append("")
            
            # Search patterns in HTML
            html_text = html_content.lower()
            found_patterns = [p for p in PATTERNS if p in html_text]
            audit_lines.append(f"**Patterns found in HTML:** {', '.join(found_patterns)}")
            
            # Analyze JS bundles
            bundle_patterns_found = {}
            api_endpoints = []
            for b in js_bundles:
                try:
                    br = requests.get(b, headers=headers, timeout=10)
                    if br.status_code == 200:
                        b_text = br.text.lower()
                        b_found = [p for p in PATTERNS if p in b_text]
                        bundle_patterns_found[b] = b_found
                        
                        # simple regex to find API endpoints
                        urls = re.findall(r'["\'](https?://[^"\']+|/[^"\']+)["\']', br.text)
                        for u in urls:
                            if 'api' in u.lower() or 'json' in u.lower():
                                api_endpoints.append(u)
                except Exception as e:
                    audit_lines.append(f"Failed to fetch bundle {b}: {e}")

            audit_lines.append("")
            audit_lines.append("**Patterns found in JS bundles:**")
            for b, p in bundle_patterns_found.items():
                audit_lines.append(f"- {b}: {', '.join(p)}")
            
            audit_lines.append("")
            audit_lines.append("**Potential API Endpoints found in bundles:**")
            for e in set(api_endpoints):
                audit_lines.append(f"- {e}")
                candidates.append({"type": "api_endpoint", "url": e})

            if len(api_endpoints) > 0:
                decision = "PARTIAL"
                status_msg = "candidate endpoints/assets found, manual inspection needed"
            elif len(js_bundles) > 0:
                decision = "PARTIAL"
                status_msg = "candidate endpoints/assets found, manual inspection needed"
            else:
                decision = "PARTIAL"
                status_msg = "manual browser network inspection required"

        else:
            decision = "PARTIAL"
            status_msg = "manual browser network inspection required"
            audit_lines.append("Failed to fetch main page with 200 OK.")

    except Exception as e:
        audit_lines.append(f"**Error:** {e}")
        decision = "PARTIAL"
        status_msg = "manual browser network inspection required"

    audit_lines.append("")
    audit_lines.append(f"**Decision:** {decision}: {status_msg}")

    # Write audit report
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(audit_lines))
    
    # Write candidates report
    for c in candidates:
        candidate_lines.append(f"- **{c['type']}**: {c['url']}")
    
    if not candidates:
        candidate_lines.append("No candidates found.")

    with open(candidates_report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(candidate_lines))

    # Write CSV
    headers = [
        "source_system", "product_name", "source_url", "top_flavors",
        "flavor_vector", "similar_whiskies", "matched_master_whisky_id",
        "match_score", "match_status", "approval_status", "import_recommendation"
    ]
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

    print(f"Audit completed. Decision: {decision}: {status_msg}")

if __name__ == '__main__':
    run_audit()
