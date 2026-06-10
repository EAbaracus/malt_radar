import requests
import json
import os

BASE_URL = "https://whiskeyfyi.com/api/v1"
ENDPOINTS = {
    "whiskeys": "/whiskeys/",
    "distilleries": "/distilleries/",
    "regions": "/regions/",
    "glossary": "/glossary/"
}
FILES = {
    "whiskeys": "03_sample_whiskeys_raw.json",
    "distilleries": "04_sample_distilleries_raw.json",
    "regions": "05_sample_regions_raw.json",
    "glossary": "06_sample_glossary_raw.json",
}

report_lines = []
schema_summary = []
schema_summary.append("endpoint,fields")

for name, ep in ENDPOINTS.items():
    url = BASE_URL + ep
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        report_lines.append(f"Endpoint {ep}: Status {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            with open(FILES[name], "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            report_lines.append(f"  - Saved sample to {FILES[name]}")
            
            # Analyze schema
            if isinstance(data, list) and len(data) > 0:
                fields = list(data[0].keys())
            elif isinstance(data, dict) and "results" in data and len(data["results"]) > 0:
                fields = list(data["results"][0].keys())
            elif isinstance(data, dict) and "data" in data and len(data["data"]) > 0:
                fields = list(data["data"][0].keys())
            elif isinstance(data, dict):
                fields = list(data.keys())
            else:
                fields = []
            schema_summary.append(f"{ep},\"{','.join(fields)}\"")
        else:
            report_lines.append(f"  - Failed to fetch sample.")
            schema_summary.append(f"{ep},\"\"")
    except Exception as e:
        report_lines.append(f"Endpoint {ep}: ERROR - {str(e)}")
        schema_summary.append(f"{ep},\"\"")

with open("07_sample_parse_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))

with open("02_endpoint_schema_summary.csv", "w", encoding="utf-8") as f:
    f.write("\n".join(schema_summary))
