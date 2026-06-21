import os
import csv
import argparse
import requests
import time
import sys

# Add current dir to path to import url_safety
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import url_safety

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
snapshots_dir = os.path.join(output_dir, "tasting_note_snapshots")
reports_dir = os.path.join(base_dir, "output", "reports")

os.makedirs(snapshots_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

index_csv_path = os.path.join(output_dir, "web_tasting_note_snapshots_index.csv")

OUT_FIELDS = [
    "whisky_id", "whisky_name", "source_url", "source_domain", "source_type",
    "snapshot_path", "http_status", "fetch_status", "match_score", "mismatch_flags"
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, default=os.path.join(output_dir, "web_tasting_note_candidates_pilot.csv"))
    args = parser.parse_args()
    
    print(f"Starting Fetch Pipeline with input: {args.input}")
    
    if not os.path.exists(args.input):
        # Allow running even if relative path given
        alt_path = os.path.join(base_dir, args.input)
        if os.path.exists(alt_path):
            args.input = alt_path
        else:
            print(f"Error: {args.input} not found.")
            return
            
    with open(args.input, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
        
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    success_count = 0
    fail_count = 0
    
    for idx, row in enumerate(reader):
        w_id = row.get("whisky_id", f"UNKNOWN_{idx}")
        w_name = row.get("whisky_name", "")
        s_url = row.get("source_url", "")
        
        out = {
            "whisky_id": w_id,
            "whisky_name": w_name,
            "source_url": s_url,
            "source_domain": row.get("source_domain", ""),
            "source_type": row.get("source_type", "unknown"),
            "snapshot_path": "",
            "http_status": "",
            "fetch_status": "pending",
            "match_score": row.get("match_score", ""),
            "mismatch_flags": row.get("mismatch_flags", "")
        }
        
        if not s_url:
            out["fetch_status"] = "invalid_url"
            results.append(out)
            fail_count += 1
            continue
            
        host = url_safety.normalize_hostname(s_url)
        if not host or url_safety.is_allowed_web_tasting_note_url(s_url, {"example.com"}):
            out["fetch_status"] = "invalid_url"
            results.append(out)
            fail_count += 1
            continue
            
        try:
            print(f"Fetching {s_url}")
            resp = requests.get(s_url, headers=headers, timeout=15)
            out["http_status"] = str(resp.status_code)
            
            if resp.status_code == 200:
                html_path = os.path.join(snapshots_dir, f"{w_id}_{idx}.html")
                with open(html_path, 'w', encoding='utf-8') as hf:
                    hf.write(resp.text)
                out["snapshot_path"] = html_path
                out["fetch_status"] = "success"
                success_count += 1
            else:
                out["fetch_status"] = f"failed_http_{resp.status_code}"
                fail_count += 1
                
        except Exception as e:
            out["fetch_status"] = f"error"
            fail_count += 1
            
        results.append(out)
        time.sleep(1) # Be polite

    with open(index_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(results)
        
    r1_path = os.path.join(reports_dir, "219_web_tasting_note_real_snapshot_report.md")
    with open(r1_path, 'w', encoding='utf-8') as f:
        f.write("# Web Tasting Note Real Snapshot Report\n\n")
        f.write(f"- Total inputs processed: {len(results)}\n")
        f.write(f"- Fetch Success: {success_count}\n")
        f.write(f"- Fetch Failed/Invalid: {fail_count}\n")

    print(f"Fetch Pipeline finished. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()
