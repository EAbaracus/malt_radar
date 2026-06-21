from __future__ import annotations

from copy import deepcopy
from typing import Any


class SourceGuard:
    PUBLIC_FORBIDDEN_SOURCE_FIELDS = {
        "source_id",
        "source_name",
        "source_url",
        "source_system",
        "source_reference",
        "internal_source_url",
        "internal_source_id",
        "internal_audit_url",
    }

    @classmethod
    def sanitize_response(cls, data: dict[str, Any], is_manual: bool = False) -> dict[str, Any]:
        sanitized = deepcopy(data)

        if is_manual:
            return sanitized

        for key in cls.PUBLIC_FORBIDDEN_SOURCE_FIELDS:
            sanitized.pop(key, None)

        return sanitized

    @classmethod
    def sanitize_collection(cls, rows: list[dict[str, Any]], is_manual: bool = False) -> list[dict[str, Any]]:
        return [cls.sanitize_response(row, is_manual=is_manual) for row in rows]