from pydantic import BaseModel, Field
from typing import List, Optional

class WhiskySearchItem(BaseModel):
    external_id: str = Field(..., description="Unique identifier for the whisky from the external source")
    name: str = Field(..., description="Name of the whisky")
    country: str = Field(..., description="Country of origin")
    region: str = Field(..., description="Region within the country")
    category: str = Field(..., description="Whisky category, e.g. Single Malt, Blend")
    age: Optional[int] = Field(None, description="Age of the whisky in years")
    abv: Optional[float] = Field(None, description="Alcohol By Volume percentage")
    cask_type: str = Field(..., description="Cask type used for aging")
    tasting_notes: List[str] = Field(default_factory=list, description="Tasting notes tags")
    companion_suggestions: List[str] = Field(default_factory=list, description="Food or activity pairing suggestions")
    default_price: float = Field(..., description="Default estimated price")
    currency: str = Field(..., description="Currency of default price (e.g. TL, USD)")
    source_name: str = Field(..., description="Source provider name")
    source_url: str = Field(..., description="Direct URL to source page")

class WhiskyPriceItem(BaseModel):
    source_name: str
    price: float
    currency: str
    country: str
    source_url: str
    fetched_at: str
    is_manual: bool

class NormalizeRequest(BaseModel):
    name: str
