import requests
import json
import csv

BASE_URL = "https://whiskeyfyi.com/api/v1"
ENDPOINTS = [
    "/whiskeys/",
    "/distilleries/",
    "/regions/",
    "/glossary/",
    "/guides/",
    "/openapi.json"
]

report = []

for ep in ENDPOINTS:
    url = BASE_URL + ep
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        report.append({"endpoint": ep, "status_code": r.status_code, "reason": r.reason})
        if ep == "/openapi.json" and r.status_code == 200:
            with open("01_openapi_raw.json", "w", encoding="utf-8") as f:
                f.write(r.text)
    except Exception as e:
        report.append({"endpoint": ep, "status_code": "ERROR", "reason": str(e)})

with open("00_api_feasibility_report.txt", "w", encoding="utf-8") as f:
    f.write("API FEASIBILITY REPORT\n")
    f.write("========================\n")
    for row in report:
        f.write(f"Endpoint: {row['endpoint']} - Status: {row['status_code']} - {row['reason']}\n")
    
    if all(r["status_code"] in [404, "ERROR", 403] for r in report):
        f.write("\nCONCLUSION: The API is not accessible. Full run is not feasible.\n")
    else:
        f.write("\nCONCLUSION: API has accessible endpoints.\n")
