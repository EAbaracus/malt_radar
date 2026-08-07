from typing import List, Optional
from app.providers.base import WhiskyProvider
from app.models.schemas import WhiskySearchItem, WhiskyPriceItem


class ManualProvider(WhiskyProvider):
    def get_name(self) -> str:
        return "Manual"

    def search(self, query: str) -> List[WhiskySearchItem]:
        return []  # Manual doesn't support searching online database

    def get_details(self, external_id: str) -> Optional[WhiskySearchItem]:
        return None

    def get_prices(self, external_id: str) -> List[WhiskyPriceItem]:
        return []
