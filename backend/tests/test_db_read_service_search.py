import pytest
from unittest.mock import MagicMock, patch
from app.services.db_read_service import DbReadService

@pytest.fixture
def service():
    return DbReadService()

def test_search_empty_query(service):
    """Test search with empty or short query returns empty list."""
    assert service.search("") == []
    assert service.search("a") == []
    assert service.search("  ") == []
    assert service.search(" a ") == []


def test_search_deduplication(service):
    """Test that search results are deduplicated by canonical name."""
    with patch.object(service, '_get_connection') as mock_conn:
        mock_cursor = MagicMock()
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor

        # Simulate cursor.fetchall() returning duplicate records by canonical name
        mock_cursor.fetchall.return_value = [
            {"whisky_id": "GSD-CAND-001", "name": "  Laphroaig 10  ", "superseded_by": None},
            {"whisky_id": "W-002", "name": "Laphroaig 10", "superseded_by": None},
            {"whisky_id": "W-003", "name": "laphroaig 10", "superseded_by": None},
            {"whisky_id": "W-004", "name": "Ardbeg 10", "superseded_by": None},
            {"whisky_id": "W-005", "name": None, "superseded_by": None}, # Missing name test case
        ]

        # Patch _prepare_whisky to simply return the input so we don't need real DB or other mocks
        with patch.object(service, '_prepare_whisky', side_effect=lambda x: x):
            results = service.search("Laphroaig")

            # Should have 3 unique names: "laphroaig 10", "ardbeg 10", and ""
            assert len(results) == 3
            assert results[0]["whisky_id"] == "GSD-CAND-001"
            assert results[0]["name"] == "  Laphroaig 10  "

            assert results[1]["whisky_id"] == "W-004"
            assert results[1]["name"] == "Ardbeg 10"

            assert results[2]["whisky_id"] == "W-005"
            assert results[2]["name"] is None
