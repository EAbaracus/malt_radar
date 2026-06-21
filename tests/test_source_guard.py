from backend.app.utils.source_guard import SourceGuard


def test_source_guard_removes_external_source_fields():
    data = {
        "name": "Lagavulin 16",
        "source_name": "Whisky Advocate",
        "source_url": "https://example.com/review",
        "source_id": "wa",
        "internal_source_url": "https://internal.example.com",
    }

    sanitized = SourceGuard.sanitize_response(data)

    assert sanitized["name"] == "Lagavulin 16"
    assert "source_name" not in sanitized
    assert "source_url" not in sanitized
    assert "source_id" not in sanitized
    assert "internal_source_url" not in sanitized


def test_source_guard_does_not_mutate_original_data():
    data = {
        "name": "Lagavulin 16",
        "source_name": "Whisky Advocate",
        "source_url": "https://example.com/review",
    }

    sanitized = SourceGuard.sanitize_response(data)

    assert "source_name" in data
    assert "source_url" in data
    assert "source_name" not in sanitized
    assert "source_url" not in sanitized


def test_source_guard_keeps_manual_data_when_explicitly_allowed():
    data = {
        "source_name": "Kişisel Takip",
        "source_url": "",
    }

    sanitized = SourceGuard.sanitize_response(data, is_manual=True)

    assert sanitized["source_name"] == "Kişisel Takip"
    assert sanitized["source_url"] == ""