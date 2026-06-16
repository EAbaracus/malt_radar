import os
import sys
import csv
from fastapi.testclient import TestClient

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(base_dir, "backend"))

from app.main import app

client = TestClient(app)

def run_validation():
    print("--- Backend Endpoint Validation ---")
    
    health_res = client.get("/api/db/health")
    print(f"Health: {health_res.status_code}")
    
    whiskies_res = client.get("/api/db/whiskies?limit=10&offset=0")
    whiskies_data = whiskies_res.json()
    db_whiskies = whiskies_data.get("items", [])
    total_count = whiskies_data.get("total_count", 0)
    print(f"Whiskies List: {whiskies_res.status_code}, count: {len(db_whiskies)}, total_count: {total_count}")
    
    dist_res = client.get("/api/db/distilleries?limit=5&offset=0")
    dist_data = dist_res.json()
    dist_items = dist_data.get("items", [])
    dist_total = dist_data.get("total_count", 0)
    print(f"Distilleries List: {dist_res.status_code}, count: {len(dist_items)}, total_count: {dist_total}")
    
    schema_res = client.get("/api/db/schema")
    print(f"Schema: {schema_res.status_code}")
    
    # Legacy CSV search to get 10 whiskies
    legacy_res = client.get("/api/whiskies/search?q=")
    legacy_whiskies = legacy_res.json()[:10]
    
    # CSV generation
    csv_path = os.path.join(base_dir, "output", "filestructure", "35_frontend_csv_vs_db_comparison.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "sample_no", "legacy_id", "db_id", "legacy_name", "db_name", 
            "legacy_distillery", "db_distillery", "legacy_country", "db_country", 
            "legacy_region", "db_region", "legacy_category", "db_category", 
            "legacy_age", "db_age", "legacy_abv", "db_abv", 
            "legacy_has_flavor", "db_has_flavor", "db_has_tasting_notes", 
            "db_has_price_history", "comparison_status", "notes"
        ])
        
        for i in range(10):
            # Try to get legacy whisky if available
            l_w = legacy_whiskies[i] if i < len(legacy_whiskies) else {}
            l_id = l_w.get("external_id")
            
            db_w = {}
            db_has_flavor = False
            db_has_tasting_notes = False
            db_has_price_history = False
            status = "DB Only"
            notes = "Legacy CSV not found or empty"
            
            # If we have legacy, try to fetch matching DB
            if l_id:
                db_w_res = client.get(f"/api/db/whiskies/{l_id}")
                if db_w_res.status_code == 200:
                    db_w = db_w_res.json()
                    status = "Match Found"
                    notes = "Same ID in both sources"
                else:
                    status = "ID Mismatch"
                    notes = "Legacy ID not found in canonical DB"
                    # Just use a random db whisky for layout
                    db_w = db_whiskies[i] if i < len(db_whiskies) else {}
            else:
                # No legacy, just use DB whisky
                db_w = db_whiskies[i] if i < len(db_whiskies) else {}
                
            db_id = db_w.get("whisky_id")
            if db_id:
                db_has_flavor = client.get(f"/api/db/whiskies/{db_id}/flavor-profile").status_code == 200
                db_tn_res = client.get(f"/api/db/whiskies/{db_id}/tasting-notes")
                db_has_tasting_notes = db_tn_res.status_code == 200 and len(db_tn_res.json()) > 0
                db_ph_res = client.get(f"/api/db/whiskies/{db_id}/price-history")
                db_has_price_history = db_ph_res.status_code == 200 and len(db_ph_res.json()) > 0

            writer.writerow([
                i+1, l_id, db_id, l_w.get("name"), db_w.get("name"),
                l_w.get("distillery"), db_w.get("distillery"), l_w.get("country"), db_w.get("country"),
                l_w.get("region"), db_w.get("region"), l_w.get("category"), db_w.get("category"),
                l_w.get("age"), db_w.get("stated_age"), l_w.get("abv"), db_w.get("abv"),
                bool(l_w.get("flavor_profile")), db_has_flavor, db_has_tasting_notes,
                db_has_price_history, status, notes
            ])

if __name__ == "__main__":
    run_validation()
    print("DONE")
