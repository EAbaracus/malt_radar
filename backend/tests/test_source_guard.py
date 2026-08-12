import pytest

from app.utils.source_guard import SourceGuard


@pytest.fixture
def sample_data():
    return {
        "id": 1,
        "name": "Test Whisky",
        "source_id": "src_123",
        "source_name": "Test Source",
        "source_url": "http://example.com/source",
        "source_domain": "example.com",
        "source_system": "sys_1",
        "source_reference": "ref_456",
        "internal_source_url": "http://internal/src_123",
        "internal_source_id": "int_123",
        "internal_audit_url": "http://audit/src_123",
        "other_field": "keep_me"
    }


def test_sanitize_response_removes_forbidden_fields(sample_data):
    """Test that forbidden fields are removed when is_manual=False."""
    result = SourceGuard.sanitize_response(sample_data, is_manual=False)

    # Check that forbidden fields are gone
    for field in SourceGuard.PUBLIC_FORBIDDEN_SOURCE_FIELDS:
        assert field not in result

    # Check that other fields remain
    assert result["id"] == 1
    assert result["name"] == "Test Whisky"
    assert result["other_field"] == "keep_me"


def test_sanitize_response_keeps_forbidden_fields_when_manual(sample_data):
    """Test that forbidden fields are kept when is_manual=True."""
    result = SourceGuard.sanitize_response(sample_data, is_manual=True)

    # Check that all original fields are still present
    for key, value in sample_data.items():
        assert result[key] == value


def test_sanitize_response_does_not_mutate_original(sample_data):
    """Test that the original dictionary is not mutated."""
    original_copy = dict(sample_data)

    SourceGuard.sanitize_response(sample_data, is_manual=False)

    assert sample_data == original_copy


def test_sanitize_response_with_missing_forbidden_fields():
    """Test that it doesn't fail if some forbidden fields are already missing."""
    data = {
        "id": 1,
        "source_id": "src_123"
        # other forbidden fields are missing
    }

    result = SourceGuard.sanitize_response(data, is_manual=False)

    assert "source_id" not in result
    assert result["id"] == 1


def test_sanitize_collection(sample_data):
    """Test that sanitize_collection correctly sanitizes a list of dictionaries."""
    data_list = [sample_data, sample_data.copy()]
    # Modify second item slightly to ensure they are distinct in some way
    data_list[1]["id"] = 2

    result = SourceGuard.sanitize_collection(data_list, is_manual=False)

    assert len(result) == 2

    for item in result:
        for field in SourceGuard.PUBLIC_FORBIDDEN_SOURCE_FIELDS:
            assert field not in item

    assert result[0]["id"] == 1
    assert result[1]["id"] == 2


def test_sanitize_collection_manual(sample_data):
    """Test that sanitize_collection correctly handles is_manual=True."""
    data_list = [sample_data, sample_data.copy()]

    result = SourceGuard.sanitize_collection(data_list, is_manual=True)

    assert len(result) == 2
    for item in result:
        for field in SourceGuard.PUBLIC_FORBIDDEN_SOURCE_FIELDS:
            assert field in item
