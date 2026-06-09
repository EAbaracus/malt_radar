import csv
import os
import uuid
from typing import List, Optional, Union
from app.providers.base import WhiskyProvider
from app.models.schemas import WhiskySearchItem, WhiskyPriceItem

class CsvWhiskyProvider(WhiskyProvider):
    def __init__(self, csv_paths: Union[str, List[str]] = "data/whisky.csv"):
        if isinstance(csv_paths, str):
            self.csv_paths = [csv_paths]
        else:
            self.csv_paths = csv_paths
        self.whiskies: List[WhiskySearchItem] = []
        self._load_data()

    def get_name(self) -> str:
        return "CSV Database"

    def _load_data(self):
        for path in self.csv_paths:
            if not os.path.exists(path):
                print(f"Warning: CSV file not found at {path}. Waiting for user to add it.")
                continue

            try:
                with open(path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    
                    for row in reader:
                        name = row.get('Adı') or row.get('name') or row.get('Name') or row.get('Company') or row.get('Whisky') or row.get('whisky')
                        if not name:
                            continue
                            
                        category = row.get('category') or row.get('Category') or row.get('type') or "Single Malt"
                        country = row.get('Menşei') or row.get('country') or row.get('Country') or "Scotland"
                        region = row.get('region') or row.get('Region') or "Unknown"
                        
                        price_str = row.get('price') or row.get('Price') or "0"
                        try:
                            price = float(price_str.replace('$', '').replace(',', '').strip()) if price_str else 0.0
                        except:
                            price = 0.0
                            
                        rating_str = row.get('Puan') or row.get('Rating') or row.get('rating') or row.get('Score') or row.get('score')
                        try:
                            global_rating = float(rating_str) if rating_str else None
                        except:
                            global_rating = None
                            
                        cask_type = row.get('Fıçı Türü') or row.get('Cask Type') or "Unknown"
                        
                        age_str = row.get('Yaşı') or row.get('Age')
                        try:
                            age = int(age_str) if age_str else None
                        except:
                            age = None

                        tasting_notes = []
                        if row.get('Burun'): tasting_notes.append(f"Burun: {row.get('Burun')}")
                        if row.get('Damak'): tasting_notes.append(f"Damak: {row.get('Damak')}")
                        if row.get('Bitiş'): tasting_notes.append(f"Bitiş: {row.get('Bitiş')}")
                        
                        notes_str = row.get('description') or row.get('Review') or row.get('notes') or ""
                        if notes_str:
                            tasting_notes.extend([n.strip() for n in notes_str.split(',') if n.strip()])

                        companion_suggestions = []
                        if row.get('Eşlikçi'):
                            companion_suggestions.extend([c.strip() for c in row.get('Eşlikçi').split(',') if c.strip()])

                        item = WhiskySearchItem(
                            external_id=f"csv-{uuid.uuid4().hex[:8]}",
                            name=name,
                            country=country,
                            region=region,
                            category=category,
                            age=age,
                            default_price=price,
                            currency="USD",
                            tasting_notes=tasting_notes,
                            companion_suggestions=companion_suggestions,
                            cask_type=cask_type,
                            global_rating=global_rating,
                            source_name="Local CSV",
                            source_url="https://local"
                        )
                        self.whiskies.append(item)
                print(f"Successfully loaded {len(self.whiskies)} whiskies so far from CSVs.")
            except Exception as e:
                print(f"Error loading CSV data from {path}: {e}")

    def search(self, query: str) -> List[WhiskySearchItem]:
        query = query.lower()
        results = [w for w in self.whiskies if query in w.name.lower()]
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
