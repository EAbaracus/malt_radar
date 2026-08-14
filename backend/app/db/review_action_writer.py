"""ReviewActionWriter — admin queue action (write-only).

Faz B (spec §4 madde 03): ReviewQueryService write metodu ayrılır.
Read/write ayrı module'de kalır (interface yalan söylemesin).

execute_action şu an: staging tablosunu UPDATE + review_actions INSERT.
Bu, staging-scope'lu bir queue aksiyonudur → G2: otomatik backup+SHA,
senkron insan GO yok (API key = zaten insan tetiklemesi).

Guard path (Faz 0): get_write_connection(authorized_context="admin_review_execute_action").
Bu module sadece oraya delegate eder.
"""
from __future__ import annotations

import datetime
import logging
import secrets
from typing import List, Dict, Any

from app.db.write_guard import get_write_connection  # canonical gate (Faz 0)
from app.utils.shared_paths import _sha256_file, ALLOWED_TABLES


class ReviewActionWriter:
    """Write-only adapter for staging queue approval actions.

    production.db'ye yazı yalnızca write_guard.get_write_connection üzerinden.
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            db_path = "output/import/production.db"
        self._write_path = db_path

    def execute_action(self, source_table: str, source_record_key: str,
                       target_status: str, action_type: str,
                       reviewer: str, reviewer_note: str,
                       previous_status: str) -> str:
        ALLOWED = ALLOWED_TABLES.get(source_table)
        if not ALLOWED:
            raise Exception("Invalid source table")
        safe_table = ALLOWED

        pre_sha = _sha256_file(self._write_path)
        key_col = ("queue_id" if safe_table == "staging_manual_review_queue"
                   else "source_record_key")
        action_id = "ra_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f") + "_" + secrets.token_hex(4)

        with get_write_connection(
            authorized_context="admin_review_execute_action",
            restrict_tables=[safe_table, "review_actions"],
            db_path=self._write_path,
        ) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.cursor()
            cur.execute(
                f"UPDATE {safe_table} SET approval_status = ? "
                f"WHERE {key_col} = ?",
                (target_status, source_record_key),
            )
            cur.execute("""
                INSERT INTO review_actions
                (action_id, source_table, source_record_key, review_status,
                 action_type, reviewer, reviewer_note, previous_status,
                 new_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (action_id, source_table, str(source_record_key), target_status,
                  action_type, reviewer, reviewer_note, previous_status, target_status))

        post_sha = _sha256_file(self._write_path)
        logging.info(
            "execute_action audit: table=%s key=%s action=%s status=%s "
            "pre_sha=%s post_sha=%s",
            safe_table, source_record_key, action_type, target_status,
            pre_sha[:16], post_sha[:16],
        )
        return action_id
