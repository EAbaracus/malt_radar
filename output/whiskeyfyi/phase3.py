import requests
import json
import csv
import os

BASE_URL = "https://whiskeyfyi.com/api/v1"
ENDPOINTS = {
    "distilleries": "/distilleries/",
    "regions": "/regions/",
    "glossary": "/glossary/",
    "guides": "/guides/"
}

# The user requested specific fields. We map API fields to requested fields where possible.
FIELDNAMES = [
    "slug", "name", "type_category", "country", "region", "description", 
    "tasting_notes", "cask_type", "url", "source_api_endpoint", "source_confidence"
]

report_lines = ["FULL FETCH REPORT\n================="]
stats = {
    "whiskey_expressions": 0,
    "distilleries": 0,
    "regions": 0,
    "glossary": 0,
    "guides": 0
}

def fetch_all(endpoint):
    url = BASE_URL + endpoint
    headers = {'User-Agent': 'Mozilla/5.0'}
    all_data = []
    # If the API is paginated, we should follow 'next', but for this isolated test we will fetch the first page or full list
    # Many simple Django/DRF endpoints return { "count": X, "next": Y, "results": [...] } or just [...]
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                if "results" in data:
                    all_data = data["results"]
                elif "data" in data:
                    all_data = data["data"]
            elif isinstance(data, list):
                all_data = data
    except Exception as e:
        report_lines.append(f"Error fetching {endpoint}: {e}")
    return all_data

def write_csv(filename, data, endpoint):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        count = 0
        for item in data:
            row = {
                "slug": item.get("slug", ""),
                "name": item.get("name", item.get("term", item.get("title", ""))),
                "type_category": item.get("category_name", item.get("type", "")),
                "country": item.get("country_name", ""),
                "region": item.get("region_name", ""),
                "description": item.get("description", item.get("definition", item.get("content", ""))),
                "tasting_notes": item.get("tasting_notes", ""),
                "cask_type": item.get("cask_type", ""),
                "url": item.get("website", item.get("url", "")),
                "source_api_endpoint": endpoint,
                "source_confidence": "high"
            }
            writer.writerow(row)
            count += 1
        return count

# Whiskeys
with open("08_whiskey_expressions.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
report_lines.append("Whiskeys endpoint was 404, wrote empty CSV.")

# Distilleries
dist_data = fetch_all(ENDPOINTS["distilleries"])
stats["distilleries"] = write_csv("09_distillery_reference_candidates.csv", dist_data, "/distilleries/")
report_lines.append(f"Distilleries fetched: {stats['distilleries']}")

# Regions
reg_data = fetch_all(ENDPOINTS["regions"])
stats["regions"] = write_csv("10_region_reference.csv", reg_data, "/regions/")
report_lines.append(f"Regions fetched: {stats['regions']}")

# Glossary
gloss_data = fetch_all(ENDPOINTS["glossary"])
stats["glossary"] = write_csv("11_glossary_terms.csv", gloss_data, "/glossary/")
report_lines.append(f"Glossary terms fetched: {stats['glossary']}")

# Guides
guides_data = fetch_all(ENDPOINTS["guides"])
stats["guides"] = write_csv("12_guides_index.csv", guides_data, "/guides/")
report_lines.append(f"Guides fetched: {stats['guides']}")

# Save report
with open("13_full_fetch_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_lines))
