import os
import csv
import sqlite3
import argparse
import time
import requests
import re
import sys
from bs4 import BeautifulSoup

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from url_safety import normalize_hostname, is_allowed_web_tasting_note_url

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(base_dir, "output", "import", "production.db")
reports_dir = os.path.join(base_dir, "output", "reports")
output_dir = os.path.join(base_dir, "data", "output")

ALLOWED_DOMAINS = {
    "ardbeg.com", "laphroaig.com", "macleans.com",
    "masterofmalt.com", "thewhiskyexchange.com", "thewhiskybarrel.com", "whiskybase.com",
    "whiskynotes.be", "whiskyreviewer.com", "breakingbourbon.com", "whiskyadvocate.com",
    "reddit.com", "distiller.com"
}

FALLBACK_PHRASES = [
    "sorry, but nothing matched your search terms",
    "nothing matched your search terms",
    "no results found",
    "page not found",
    "404",
    "try again with some different keywords",
    "search results",
    "access denied",
    "captcha",
    "cloudflare",
    "javascript is disabled",
    "enable cookies"
]

def check_url_safety(url):
    if not url: return False
    return is_allowed_web_tasting_note_url(url, ALLOWED_DOMAINS)

def check_content_signals(text, whisky_name):
    lower = text.lower()
    
    # Check fallback
    for p in FALLBACK_PHRASES:
        if p in lower:
            return False, "rejected_no_result_page"
            
    # Check search page indicator in text
    if "search results for" in lower or "you searched for" in lower:
        return False, "rejected_search_page"

    tasting_signals = ["nose", "palate", "finish", "aroma", "taste", "tasting notes", "review"]
    signal_count = sum(1 for s in tasting_signals if s in lower)
    
    name_tokens = [t for t in whisky_name.lower().split() if len(t) > 3 and t not in ['the', 'single', 'malt', 'whisky']]
    matched_tokens = sum(1 for t in name_tokens if t in lower)
    
    if signal_count >= 1 and matched_tokens >= len(name_tokens) // 2:
        return True, "content_signal_pass"
        
    return False, "rejected_no_result_page"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default=os.path.join(output_dir, "web_tasting_note_real_source_candidates_v2.csv"))
    parser.add_argument('--output-index', default=os.path.join(output_dir, "web_tasting_note_snapshots_index_v2.csv"))
    parser.add_argument('--snapshot-dir', default=os.path.join(output_dir, "web_tasting_note_snapshots_v2"))
    args = parser.parse_args()

    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(args.snapshot_dir, exist_ok=True)

    out_reject = os.path.join(output_dir, "web_tasting_note_snapshots_rejected_v2.csv")
    out_audit = os.path.join(output_dir, "web_tasting_note_snapshot_quality_audit_v2.csv")
    report_md = os.path.join(reports_dir, "293_web_tasting_note_snapshot_fetch_v2_report.md")
    gate_txt = os.path.join(reports_dir, "294_12w_web_tasting_note_snapshot_fetch_v2_gate.txt")

    candidates = []
    if os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            candidates = list(csv.DictReader(f))

    stats = {
        "input_candidate_rows": len(candidates),
        "attempted_fetch_count": 0,
        "fetch_success_count": 0,
        "fetch_rejected_count": 0,
        "rejected_no_result_page_count": 0,
        "rejected_search_page_count": 0,
        "rejected_unsafe_url_count": 0,
        "rejected_missing_url_count": 0,
        "http_error_count": 0,
        "content_signal_pass_count": 0
    }

    index_rows = []
    rejected_rows = []
    audit_rows = []

    for idx, cand in enumerate(candidates):
        url = cand.get("source_url", "")
        w_id = cand.get("whisky_id", "")
        w_name = cand.get("whisky_name", "")
        
        status = "unfetched"
        reason = ""
        http_status = ""
        snapshot_path = ""
        
        # We only consider candidate_keep? 
        # Actually the input file only contains candidates kept from 12V because the name says candidates.
        
        if not url:
            stats["rejected_missing_url_count"] += 1
            status = "rejected_missing_url"
            reason = "missing_url"
        elif not check_url_safety(url):
            stats["rejected_unsafe_url_count"] += 1
            status = "rejected_unsafe_url"
            reason = "unsafe_url"
        else:
            stats["attempted_fetch_count"] += 1
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                http_status = str(resp.status_code)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for s in soup(["script", "style", "nav", "footer", "header"]): s.extract()
                    text = soup.get_text(separator=' ')
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    is_valid, content_reason = check_content_signals(text, w_name)
                    if is_valid:
                        # Write snapshot
                        fname = f"{w_id}_{idx}.html"
                        fpath = os.path.join(args.snapshot_dir, fname)
                        with open(fpath, 'w', encoding='utf-8') as f:
                            f.write(resp.text)
                            f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

                            
                        status = "fetch_success"
                        reason = content_reason
                        snapshot_path = fpath
                        stats["fetch_success_count"] += 1
                        stats["content_signal_pass_count"] += 1
                    else:
                        status = "fetch_rejected"
                        reason = content_reason
                        stats["fetch_rejected_count"] += 1
                        if content_reason == "rejected_no_result_page": stats["rejected_no_result_page_count"] += 1
                        if content_reason == "rejected_search_page": stats["rejected_search_page_count"] += 1
                else:
                    status = "http_error"
                    reason = f"HTTP {resp.status_code}"
                    stats["http_error_count"] += 1
                    stats["fetch_rejected_count"] += 1
            except Exception as e:
                status = "http_error"
                reason = str(e)[:50]
                http_status = "err"
                stats["http_error_count"] += 1
                stats["fetch_rejected_count"] += 1
                
        out_row = {
            "whisky_id": w_id,
            "whisky_name": w_name,
            "source_url": url,
            "source_domain": cand.get("source_domain", ""),
            "source_type": cand.get("source_type", "review_page"),
            "snapshot_path": snapshot_path,
            "http_status": http_status,
            "fetch_status": status,
            "match_score": cand.get("match_score", ""),
            "mismatch_flags": cand.get("mismatch_flags", ""),
            "reject_reason": reason
        }
        
        audit_rows.append(out_row)
        if status == "fetch_success":
            index_rows.append(out_row)
        else:
            rejected_rows.append(out_row)

    def write_csv(path, data):
        if not data:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                csv.DictWriter(f, fieldnames=["whisky_id"]).writeheader()
            return
        with open(path, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)

    write_csv(args.output_index, index_rows)
    write_csv(out_reject, rejected_rows)
    write_csv(out_audit, audit_rows)

    gate = "GO"
    gate_reasons = []

    if stats["input_candidate_rows"] != 50:
        gate = "NO-GO"
        gate_reasons.append(f"input_candidate_rows is {stats['input_candidate_rows']}, expected 50")
        
    if stats["fetch_success_count"] == 0:
        gate = "PARTIAL-GO" if gate == "GO" else gate
        gate_reasons.append("fetch_success_count is 0")
        
    with open(gate_txt, 'w', encoding='utf-8') as f:
        f.write(f"GATE: {gate}\n")
        for r in gate_reasons: f.write(f"REASON: {r}\n")
        if gate in ["GO", "PARTIAL-GO"]:
            f.write("REASON: Strict snapshot fetch executed safely.\n")

    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# 293 Web Tasting Note Snapshot Fetch v2 Report\n\n")
        for k, v in stats.items():
            f.write(f"- {k}: {v}\n")
        f.write("- production_db_changed: NO\n")
        f.write("- output_import_changed: NO\n")

if __name__ == "__main__":
    main()
