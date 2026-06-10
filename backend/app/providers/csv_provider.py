import csv
import os
import uuid
import math
from typing import List, Optional, Union
from app.providers.base import WhiskyProvider
from app.models.schemas import WhiskySearchItem, WhiskyPriceItem

class CsvWhiskyProvider(WhiskyProvider):
    def __init__(self, csv_paths: Union[str, List[str]] = "data/whisky_database_merged_max.csv"):
        if isinstance(csv_paths, str):
            self.csv_paths = [csv_paths]
        else:
            self.csv_paths = csv_paths
        self.whiskies: List[WhiskySearchItem] = []
        self._load_data()

    def get_name(self) -> str:
        return "Merged CSV Database"

    def _load_data(self):
        import json
        
        flavor_map_by_id = {}
        flavor_map_by_name = {}
        flavor_path = "output/flavor/30_HIGH_CONFIDENCE_flavor_profiles_WDB_MAPPED.csv"
        if os.path.exists(flavor_path):
            try:
                with open(flavor_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    f_reader = csv.DictReader(f)
                    for f_row in f_reader:
                        w_id = f_row.get('whisky_id')
                        w_name = f_row.get('whisky_name')
                        
                        if w_id:
                            flavor_map_by_id[str(w_id)] = f_row
                        if w_name:
                            flavor_map_by_name[w_name] = f_row
            except Exception as e:
                print(f"Error loading flavor profiles: {e}")

        for path in self.csv_paths:
            if not os.path.exists(path):
                print(f"Warning: CSV file not found at {path}. Waiting for user to add it.")
                continue

            try:
                with open(path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    
                    for idx, row in enumerate(reader):
                        # Required fields fallback mapping just in case
                        name = row.get('whisky_name') or row.get('canonical_name') or row.get('Name') or row.get('Adı')
                        if not name:
                            continue
                            
                        category = row.get('class') or row.get('type') or row.get('category') or "Single Malt"
                        if row.get('type') and row.get('type') != row.get('class') and row.get('type'):
                            if row.get('type') not in category:
                                category = f"{category} ({row.get('type')})"
                                
                        country = row.get('country') or "Scotland"
                        region = row.get('region') or "Unknown"
                        distillery = row.get('distillery') or row.get('brand_or_company') or "Unknown"
                        cask_type = row.get('cask_type') or "Unknown"
                        if row.get('finish_type'):
                            cask_type = f"{cask_type} (Finish: {row.get('finish_type')})"
                            
                        # Price parsing
                        price_str = row.get('current_price') or row.get('price') or "0"
                        try:
                            price = float(price_str) if price_str and price_str.strip() else 0.0
                        except:
                            price = 0.0
                            
                        # Cost tier fallback
                        cost_val = row.get('cost_tier')
                        if price == 0.0 and cost_val:
                            cost_val = cost_val.strip()
                            if cost_val == '$$$$$+': price = 300.0
                            elif cost_val == '$$$$$': price = 150.0
                            elif cost_val == '$$$$': price = 70.0
                            elif cost_val == '$$$': price = 45.0
                            elif cost_val == '$$': price = 35.0
                            elif cost_val == '$': price = 20.0
                            
                        currency = row.get('price_currency') or "USD"
                        if not currency.strip(): currency = "USD"
                        
                        # Ratings parsing
                        rating_str = row.get('meta_critic') or row.get('user_score_100')
                        try:
                            if rating_str and rating_str.strip():
                                global_rating = float(rating_str)
                                # Eğer puan 10 üzerinden ise (örn: 8.5), 100 üzerinden formata çevir (85)
                                if global_rating > 0 and global_rating <= 10.0:
                                    global_rating = global_rating * 10
                            else:
                                global_rating = None
                        except:
                            global_rating = None
                            
                        # Age parsing
                        age_str = row.get('age_years') or row.get('age_raw')
                        try:
                            age = int(float(age_str)) if age_str and age_str.strip() else None
                        except:
                            age = None
                            
                        # ABV parsing
                        abv_str = row.get('abv_percent')
                        try:
                            abv = float(abv_str) if abv_str and abv_str.strip() else None
                        except:
                            abv = None

                        tasting_notes = []
                        if row.get('nose_notes'): tasting_notes.append(f"Burun: {row.get('nose_notes')}")
                        if row.get('palate_notes'): tasting_notes.append(f"Damak: {row.get('palate_notes')}")
                        if row.get('finish_notes'): tasting_notes.append(f"Bitiş: {row.get('finish_notes')}")
                        
                        notes_str = row.get('general_notes')
                        if notes_str:
                            tasting_notes.extend([n.strip() for n in notes_str.split(',') if n.strip()])
                            
                        tags_str = row.get('aroma_tags')
                        if tags_str:
                            tasting_notes.extend([n.strip() for n in tags_str.split(',') if n.strip()])
                            
                        if row.get('super_cluster'): tasting_notes.append(f"Super Cluster: {row.get('super_cluster')}")
                        if row.get('cluster'): tasting_notes.append(f"Cluster: {row.get('cluster')}")
                        
                        if row.get('smoke_level'): tasting_notes.append(f"Smoke: {row.get('smoke_level')}")
                        if row.get('peat_level'): tasting_notes.append(f"Peat: {row.get('peat_level')}")
                        if row.get('sweetness'): tasting_notes.append(f"Sweetness: {row.get('sweetness')}")
                        if row.get('spiciness'): tasting_notes.append(f"Spiciness: {row.get('spiciness')}")
                        if row.get('body'): tasting_notes.append(f"Body: {row.get('body')}")

                        companion_suggestions = []
                        if row.get('pairing_notes'):
                            companion_suggestions.extend([c.strip() for c in row.get('pairing_notes').split(',') if c.strip()])
                        if row.get('alternative_suggestions'):
                            companion_suggestions.extend([c.strip() for c in row.get('alternative_suggestions').split(',') if c.strip()])

                        item = WhiskySearchItem(
                            external_id=row.get('record_id') or f"csv-{uuid.uuid4().hex[:8]}",
                            name=name,
                            country=country,
                            region=region,
                            distillery=distillery,
                            category=category,
                            age=age,
                            abv=abv,
                            default_price=price,
                            currency=currency,
                            tasting_notes=tasting_notes,
                            companion_suggestions=companion_suggestions,
                            cask_type=cask_type,
                            global_rating=global_rating,
                            source_name="Local CSV",
                            source_url="https://local",
                            flavor_profile=None,
                            flavor_vector=None,
                            flavor_tags=None,
                            flavor_source=None,
                            flavor_match_score=None
                        )
                        
                        def normalize_str(s):
                            if not s: return ""
                            return ''.join(e for e in s.lower() if e.isalnum())
                            
                        # MAPPED CSV contains WDB-xxxxx in 'whisky_id' column, which corresponds to item.external_id
                        rec_id = item.external_id
                        
                        is_distillery = row.get('record_type', '').lower() == 'distillery' or row.get('record_type', '').lower() == 'distillery_only'
                        
                        if rec_id in flavor_map_by_id and not is_distillery:
                            f_data = flavor_map_by_id[rec_id]
                            try:
                                if f_data.get('flavor_profile'):
                                    item.flavor_profile = json.loads(f_data['flavor_profile'])
                                if f_data.get('flavor_vector'):
                                    item.flavor_vector = json.loads(f_data['flavor_vector'])
                                if f_data.get('flavor_tags'):
                                    item.flavor_tags = json.loads(f_data['flavor_tags'])
                                item.flavor_source = f_data.get('flavor_source')
                                if f_data.get('flavor_match_score'):
                                    item.flavor_match_score = float(f_data['flavor_match_score'])
                            except Exception as e:
                                print(f"Error parsing flavor JSON for id {rec_id}: {e}")
                        else:
                            # Normalized name check for risk log (fallback warning only)
                            norm_db = normalize_str(name)
                            norm_flavor_map = {normalize_str(k): v for k, v in flavor_map_by_name.items()}
                            if norm_db in norm_flavor_map and not is_distillery:
                                print(f"RISK/DEBUG: Name match found for {name} but record_id {rec_id} did not match mapped database. Skipping auto-attach.")
                        
                        self.whiskies.append(item)
                print(f"Successfully loaded {len(self.whiskies)} whiskies from CSV.")
            except Exception as e:
                print(f"Error loading CSV data from {path}: {e}")

    def search(self, query: str) -> List[WhiskySearchItem]:
        query = query.lower()
        results = [w for w in self.whiskies if query in w.name.lower() or (w.distillery and query in w.distillery.lower())]
        return results[:20]

    def get_details(self, external_id: str) -> Optional[WhiskySearchItem]:
        for w in self.whiskies:
            if w.external_id == external_id:
                return w
        return None

    def get_prices(self, external_id: str) -> List[WhiskyPriceItem]:
        for w in self.whiskies:
            if w.external_id == external_id and w.default_price > 0:
                return [
                    WhiskyPriceItem(
                        vendor="Global Store",
                        price=w.default_price,
                        currency=w.currency,
                        country="Global",
                        source_url="https://example.com/buy",
                        fetched_at="now",
                        is_manual=False
                    )
                ]
        return []
