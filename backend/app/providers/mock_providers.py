from typing import List, Optional
from datetime import datetime
from app.providers.base import WhiskyProvider
from app.models.schemas import WhiskySearchItem, WhiskyPriceItem

class BaseMockProvider(WhiskyProvider):
    def __init__(self):
        # A list of whiskies this provider "knows" about
        self.whiskies = [
            {
                "external_id": "lagavulin-16",
                "name": "Lagavulin 16",
                "country": "Scotland",
                "region": "Islay",
                "category": "Single Malt",
                "age": 16,
                "abv": 43.0,
                "cask_type": "Oak, Sherry",
                "tasting_notes": ["Peat", "Smoke", "Oak", "Sea salt"],
                "companion_suggestions": ["Dark Chocolate", "Roquefort"],
                "default_price": 4800.0,
                "currency": "TL",
                "global_rating": 93.0
            },
            {
                "external_id": "macallan-12",
                "name": "Macallan 12 Double Cask",
                "country": "Scotland",
                "region": "Speyside",
                "category": "Single Malt",
                "age": 12,
                "abv": 40.0,
                "cask_type": "Sherry, American Oak",
                "tasting_notes": ["Honey", "Vanilla", "Dried fruit", "Butterscotch"],
                "companion_suggestions": ["Dried Figs", "Mild Cheese"],
                "default_price": 4200.0,
                "currency": "TL",
                "global_rating": 88.0
            },
            {
                "external_id": "yamazaki-12",
                "name": "Yamazaki 12",
                "country": "Japan",
                "region": "Osaka",
                "category": "Single Malt",
                "age": 12,
                "abv": 43.0,
                "cask_type": "Mizunara, Sherry, Bourbon",
                "tasting_notes": ["Peach", "Pineapple", "Mizunara oak", "Orange"],
                "companion_suggestions": ["Sushi", "Dark Fruits"],
                "default_price": 9500.0,
                "currency": "TL",
                "global_rating": 90.0
            },
            {
                "external_id": "octomore-14",
                "name": "Bruichladdich Octomore 14.1",
                "country": "Scotland",
                "region": "Islay",
                "category": "Single Malt",
                "age": 5,
                "abv": 59.6,
                "cask_type": "American Oak",
                "tasting_notes": ["Heavy smoke", "Vanilla", "Citrus", "Heather honey"],
                "companion_suggestions": ["Smoked Brisket", "Very Strong Blue Cheese"],
                "default_price": 7500.0,
                "currency": "TL",
                "global_rating": 91.0
            },
            {
                "external_id": "macallan-18",
                "name": "Macallan 18 Sherry Oak",
                "country": "Scotland",
                "region": "Speyside",
                "category": "Single Malt",
                "age": 18,
                "abv": 43.0,
                "cask_type": "Sherry Oak",
                "tasting_notes": ["Dried fruit", "Ginger", "Cinnamon", "Clove"],
                "companion_suggestions": ["Dark Chocolate Truffles", "Aged Cheese"],
                "default_price": 14500.0,
                "currency": "TL",
                "global_rating": 94.0
            },
            {
                "external_id": "glenfiddich-18",
                "name": "Glenfiddich 18",
                "country": "Scotland",
                "region": "Speyside",
                "category": "Single Malt",
                "age": 18,
                "abv": 40.0,
                "cask_type": "Oloroso Sherry, Bourbon",
                "tasting_notes": ["Baked apple", "Cinnamon", "Oak", "Dates"],
                "companion_suggestions": ["Apple Pie", "Cheddar"],
                "default_price": 6200.0,
                "currency": "TL",
                "global_rating": 89.0
            },
            {
                "external_id": "hibiki-harmony",
                "name": "Hibiki Harmony",
                "country": "Japan",
                "region": "Suntory",
                "category": "Blended",
                "age": None,
                "abv": 43.0,
                "cask_type": "Mizunara, American Oak, Sherry",
                "tasting_notes": ["Honey", "Orange peel", "White chocolate", "Rose"],
                "companion_suggestions": ["Fruit Tarts", "Tempura"],
                "default_price": 8500.0,
                "currency": "TL",
                "global_rating": 87.0
            },
            {
                "external_id": "aberlour-a-bunadh",
                "name": "Aberlour A'bunadh",
                "country": "Scotland",
                "region": "Speyside",
                "category": "Single Malt",
                "age": None,
                "abv": 60.5,
                "cask_type": "Oloroso Sherry Butts",
                "tasting_notes": ["Dark Chocolate", "Spice", "Dried Fruit", "Cherry"],
                "companion_suggestions": ["Dark Chocolate", "Strong Cheddar"],
                "default_price": 4900.0,
                "currency": "TL",
                "global_rating": 89.0
            },
            {
                "external_id": "aberlour-12",
                "name": "Aberlour 12",
                "country": "Scotland",
                "region": "Speyside",
                "category": "Single Malt",
                "age": 12,
                "abv": 40.0,
                "cask_type": "Double Cask",
                "tasting_notes": ["Sherry", "Honey", "Spices", "Chocolate"],
                "companion_suggestions": ["Roasted Almonds", "Mild Cigars"],
                "default_price": 3100.0,
                "currency": "TL",
                "global_rating": 85.0
            },
            {
                "external_id": "talisker-10",
                "name": "Talisker 10",
                "country": "Scotland",
                "region": "Islands",
                "category": "Single Malt",
                "age": 10,
                "abv": 45.8,
                "cask_type": "American Oak",
                "tasting_notes": ["Smoke", "Sea Salt", "Pepper", "Peat"],
                "companion_suggestions": ["Oysters", "Smoked Salmon"],
                "default_price": 2800.0,
                "currency": "TL",
                "global_rating": 90.0
            },
            {
                "external_id": "glenlivet-18",
                "name": "The Glenlivet 18",
                "country": "Scotland",
                "region": "Speyside",
                "category": "Single Malt",
                "age": 18,
                "abv": 40.0,
                "cask_type": "First and Second Fill American Oak, Ex-Sherry",
                "tasting_notes": ["Ripe citrus", "Winter spice", "Sweet orange"],
                "companion_suggestions": ["Roast meats", "Foie gras"],
                "default_price": 5400.0,
                "currency": "TL",
                "global_rating": 92.0
            },
            {
                "external_id": "glenmorangie-10",
                "name": "Glenmorangie The Original 10",
                "country": "Scotland",
                "region": "Highland",
                "category": "Single Malt",
                "age": 10,
                "abv": 40.0,
                "cask_type": "Ex-Bourbon",
                "tasting_notes": ["Citrus", "Vanilla", "Peaches", "Soft spice"],
                "companion_suggestions": ["Vanilla dessert", "Light seafood"],
                "default_price": 2400.0,
                "currency": "TL",
                "global_rating": 86.0
            }
        ]

class WhiskyHunterProvider(BaseMockProvider):
    def get_name(self) -> str:
        return "WhiskyHunter"

    def search(self, query: str) -> List[WhiskySearchItem]:
        q = query.lower()
        results = []
        for w in self.whiskies:
            if q in w["name"].lower() or q in w["country"].lower() or q in w["region"].lower():
                results.append(WhiskySearchItem(
                    external_id=f"wh-{w['external_id']}",
                    name=w["name"],
                    country=w["country"],
                    region=w["region"],
                    category=w["category"],
                    age=w["age"],
                    abv=w["abv"],
                    cask_type=w["cask_type"],
                    tasting_notes=w["tasting_notes"],
                    companion_suggestions=w["companion_suggestions"],
                    default_price=w["default_price"],
                    currency=w["currency"],
                    global_rating=w.get("global_rating"),
                    source_name=self.get_name(),
                    source_url=f"https://whiskyhunter.com/whiskies/{w['external_id']}"
                ))
        return results

    def get_details(self, external_id: str) -> Optional[WhiskySearchItem]:
        # Strip provider prefix if present
        clean_id = external_id.replace("wh-", "")
        for w in self.whiskies:
            if w["external_id"] == clean_id:
                return WhiskySearchItem(
                    external_id=external_id,
                    name=w["name"],
                    country=w["country"],
                    region=w["region"],
                    category=w["category"],
                    age=w["age"],
                    abv=w["abv"],
                    cask_type=w["cask_type"],
                    tasting_notes=w["tasting_notes"],
                    companion_suggestions=w["companion_suggestions"],
                    default_price=w["default_price"],
                    currency=w["currency"],
                    global_rating=w.get("global_rating"),
                    source_name=self.get_name(),
                    source_url=f"https://whiskyhunter.com/whiskies/{clean_id}"
                )
        return None

    def get_prices(self, external_id: str) -> List[WhiskyPriceItem]:
        clean_id = external_id.replace("wh-", "")
        for w in self.whiskies:
            if w["external_id"] == clean_id:
                # Returns 2 historical price listings
                return [
                    WhiskyPriceItem(
                        source_name=self.get_name(),
                        price=w["default_price"],
                        currency=w["currency"],
                        country="Turkey",
                        source_url=f"https://whiskyhunter.com/whiskies/{clean_id}/price-latest",
                        fetched_at=datetime.utcnow().isoformat() + "Z",
                        is_manual=False
                    ),
                    WhiskyPriceItem(
                        source_name=self.get_name(),
                        price=w["default_price"] * 0.92,
                        currency=w["currency"],
                        country="Turkey",
                        source_url=f"https://whiskyhunter.com/whiskies/{clean_id}/price-history",
                        fetched_at="2026-05-01T12:00:00Z",
                        is_manual=False
                    )
                ]
        return []

class WhiskyEditionProvider(BaseMockProvider):
    def get_name(self) -> str:
        return "WhiskyEdition"

    def search(self, query: str) -> List[WhiskySearchItem]:
        q = query.lower()
        results = []
        for w in self.whiskies:
            if q in w["name"].lower() or q in w["country"].lower():
                # Modify prices slightly to show different source data
                results.append(WhiskySearchItem(
                    external_id=f"we-{w['external_id']}",
                    name=w["name"],
                    country=w["country"],
                    region=w["region"],
                    category=w["category"],
                    age=w["age"],
                    abv=w["abv"],
                    cask_type=w["cask_type"],
                    tasting_notes=w["tasting_notes"],
                    companion_suggestions=w["companion_suggestions"],
                    default_price=round(w["default_price"] * 1.05, -1),
                    currency=w["currency"],
                    global_rating=w.get("global_rating"),
                    source_name=self.get_name(),
                    source_url=f"https://whiskyedition.org/bottle/{w['external_id']}"
                ))
        return results

    def get_details(self, external_id: str) -> Optional[WhiskySearchItem]:
        clean_id = external_id.replace("we-", "")
        for w in self.whiskies:
            if w["external_id"] == clean_id:
                return WhiskySearchItem(
                    external_id=external_id,
                    name=w["name"],
                    country=w["country"],
                    region=w["region"],
                    category=w["category"],
                    age=w["age"],
                    abv=w["abv"],
                    cask_type=w["cask_type"],
                    tasting_notes=w["tasting_notes"],
                    companion_suggestions=w["companion_suggestions"],
                    default_price=round(w["default_price"] * 1.05, -1),
                    currency=w["currency"],
                    global_rating=w.get("global_rating"),
                    source_name=self.get_name(),
                    source_url=f"https://whiskyedition.org/bottle/{clean_id}"
                )
        return None

    def get_prices(self, external_id: str) -> List[WhiskyPriceItem]:
        clean_id = external_id.replace("we-", "")
        for w in self.whiskies:
            if w["external_id"] == clean_id:
                return [
                    WhiskyPriceItem(
                        source_name=self.get_name(),
                        price=round(w["default_price"] * 1.05, -1),
                        currency=w["currency"],
                        country="Turkey",
                        source_url=f"https://whiskyedition.org/bottle/{clean_id}/shop",
                        fetched_at=datetime.utcnow().isoformat() + "Z",
                        is_manual=False
                    )
                ]
        return []

class ManualProvider(WhiskyProvider):
    def get_name(self) -> str:
        return "Manual"

    def search(self, query: str) -> List[WhiskySearchItem]:
        return [] # Manual doesn't support searching online database

    def get_details(self, external_id: str) -> Optional[WhiskySearchItem]:
        return None

    def get_prices(self, external_id: str) -> List[WhiskyPriceItem]:
        return []
