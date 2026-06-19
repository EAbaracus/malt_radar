import os
import pytest
from unittest.mock import patch, MagicMock
from app.providers.distiller_provider import DistillerProvider

@pytest.fixture
def distiller_html_fixture():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "distiller_sample.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()

@patch('app.providers.distiller_provider.httpx.Client')
def test_distiller_scraper_contract_fixture(mock_client_class, distiller_html_fixture):
    # Setup mock
    mock_instance = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_instance
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = distiller_html_fixture
    mock_instance.get.return_value = mock_response

    # Execute
    provider = DistillerProvider()
    result = provider.get_details("ds-lagavulin-16")

    # Assertions
    assert result is not None, "Parser failed to return a result object"
    assert result.name == "Lagavulin 16", f"Expected name 'Lagavulin 16', got {result.name}"
    assert result.source_url == "https://distiller.com/spirits/lagavulin-16", f"Source URL incorrect: {result.source_url}"
    assert result.tasting_notes, "Tasting notes must not be empty"
    assert result.age == 16, f"Expected age 16, got {result.age}"
    assert result.abv == 43.0, f"Expected ABV 43.0, got {result.abv}"
    assert result.cask_type == "Ex-Bourbon", f"Expected Ex-Bourbon, got {result.cask_type}"
    assert result.global_rating == 92.0, f"Expected rating 92.0, got {result.global_rating}"
    assert result.default_price == 110.0, f"Expected price 110.0, got {result.default_price}"
    
    # Flavor notes checking via tasting_notes & companion_suggestions
    assert "Peat" in result.tasting_notes or "Smoke" in result.tasting_notes or "Sherry" in result.tasting_notes
    assert result.companion_suggestions, "Companion suggestions should be generated from flavors"
