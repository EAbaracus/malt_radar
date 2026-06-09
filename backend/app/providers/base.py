from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.schemas import WhiskySearchItem, WhiskyPriceItem

class WhiskyProvider(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Returns the name of the provider."""
        pass

    @abstractmethod
    def search(self, query: str) -> List[WhiskySearchItem]:
        """Search whiskies matching the query."""
        pass

    @abstractmethod
    def get_details(self, external_id: str) -> Optional[WhiskySearchItem]:
        """Get details for a specific whisky ID."""
        pass

    @abstractmethod
    def get_prices(self, external_id: str) -> List[WhiskyPriceItem]:
        """Get pricing listings for a specific whisky ID."""
        pass
