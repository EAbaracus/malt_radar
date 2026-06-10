from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class WhiskySearchItem(BaseModel):
    external_id: str = Field(..., description="Unique identifier for the whisky from the external source")
    name: str = Field(..., description="Name of the whisky")
    country: Optional[str] = Field(None, description="Country of origin")
    region: Optional[str] = Field(None, description="Region within the country")
    distillery: Optional[str] = Field(None, description="Distillery name")
    category: Optional[str] = Field(None, description="Whisky category, e.g. Single Malt, Blend")
    age: Optional[int] = Field(None, description="Age of the whisky in years")
    abv: Optional[float] = Field(None, description="Alcohol By Volume percentage")
    cask_type: Optional[str] = Field(None, description="Cask type used for aging")
    tasting_notes: List[str] = Field(default_factory=list, description="Tasting notes tags")
    companion_suggestions: List[str] = Field(default_factory=list, description="Food or activity pairing suggestions")
    global_rating: Optional[float] = Field(None, description="Global or community rating from 0-100")
    default_price: Optional[float] = Field(None, description="Default estimated price")
    currency: Optional[str] = Field(None, description="Currency of default price (e.g. TL, USD)")
    source_name: str = Field(..., description="Source provider name")
    source_url: str = Field(..., description="Direct URL to source page")
    # Flavor profile is a grouped high-level summary (e.g., Fruity, Smoky)
    flavor_profile: Optional[Dict[str, float]] = Field(None, description="Flavor profile grouped into main categories")
    # Flavor vector represents raw, detailed flavor intensities directly from the provider
    flavor_vector: Optional[Dict[str, float]] = Field(None, description="Detailed flavor raw data")
    flavor_tags: Optional[List[str]] = Field(None, description="Top 5 flavor tags")
    flavor_source: Optional[str] = Field(None, description="Source of the flavor profile")
    flavor_match_score: Optional[float] = Field(None, description="Confidence score of the flavor match")

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
