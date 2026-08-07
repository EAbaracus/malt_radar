"""SQLite store for accounts, sessions, email verification and per-user sync.

Uses a connection-per-operation pattern (check_same_thread=False is avoided in
favour of opening a fresh connection each time) so it is safe under FastAPI's
threadpool without holding a sqlite cursor across awaits. The DB file is
entirely separate from the governed whisky `production.db`.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

#: Session lifetime (30 days; sliding refresh on each authenticated call).
SESSION_TTL_DAYS = 30
#: Email verification token lifetime (24h).
VERIFY_TTL_HOURS = 24

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT,
  age_country TEXT,
  age_min INTEGER,
  privacy_consent INTEGER NOT NULL DEFAULT 0,
  consent_at TEXT,
  email_verified INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS email_verifications (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_favorites (
  user_id INTEGER NOT NULL,
  whisky_id TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, whisky_id)
);
CREATE TABLE IF NOT EXISTS sync_scores (
  user_id INTEGER NOT NULL,
  whisky_id TEXT NOT NULL,
  score INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, whisky_id)
);
CREATE TABLE IF NOT EXISTS sync_notes (
  user_id INTEGER NOT NULL,
  whisky_id TEXT NOT NULL,
  note TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, whisky_id)
);
CREATE TABLE IF NOT EXISTS sync_lists (
  user_id INTEGER NOT NULL,
  list_id TEXT NOT NULL,
  name TEXT NOT NULL,
  default_type TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, list_id)
);
CREATE TABLE IF NOT EXISTS sync_list_items (
  user_id INTEGER NOT NULL,
  list_id TEXT NOT NULL,
  whisky_id TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  note TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, list_id, whisky_id)
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""


class DuplicateEmailError(Exception):
    pass


class UserStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_schema()

    # --- lifecycle -----------------------------------------------------
    @classmethod
    def from_env(cls) -> "UserStore":
        path = os.getenv("MALT_RADAR_USERS_DB_PATH")
        if not path:
            base = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            )
            path = os.path.join(base, "backend", "data", "users.db")
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        return cls(path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    # --- users ---------------------------------------------------------
    def create_user(
        self,
        email: str,
        password_hash: str,
        age_country: str,
        age_min: int,
        privacy_consent: bool,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        email = email.strip().lower()
        now = self._now()
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    """INSERT INTO users
                       (email, password_hash, display_name, age_country, age_min,
                        privacy_consent, consent_at, created_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        email,
                        password_hash,
                        display_name,
                        age_country,
                        age_min,
                        1 if privacy_consent else 0,
                        now if privacy_consent else None,
                        now,
                    ),
                )
                conn.commit()
                assert cur.lastrowid is not None
                uid = int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            if "UNIQUE" in str(exc).upper() or "constraint" in str(exc).lower():
                raise DuplicateEmailError(email) from exc
            raise
        return {
            "id": uid,
            "email": email,
            "password_hash": password_hash,
            "display_name": display_name,
            "age_country": age_country,
            "age_min": age_min,
            "privacy_consent": 1 if privacy_consent else 0,
            "consent_at": now if privacy_consent else None,
            "email_verified": 0,
            "created_at": now,
        }

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self._fetch_one(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        )

    def get_user_by_id(self, uid: int) -> Optional[Dict[str, Any]]:
        return self._fetch_one("SELECT * FROM users WHERE id = ?", (uid,))

    def set_email_verified(self, uid: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE users SET email_verified = 1 WHERE id = ?", (uid,)
            )
            conn.commit()
        return cur.rowcount > 0

    def update_profile(self, uid: int, display_name: Optional[str] = None) -> None:
        sets: List[str] = []
        vals: List[Any] = []
        if display_name is not None:
            sets.append("display_name = ?")
            vals.append(display_name.strip() or None)
        if not sets:
            return
        vals.append(uid)
        with self._connect() as conn:
            conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", vals)
            conn.commit()

    def _fetch_one(self, sql: str, params: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    # --- sessions ------------------------------------------------------
    def create_session(self, uid: int) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(days=SESSION_TTL_DAYS)).isoformat(
            timespec="seconds"
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (token_hash, user_id, created_at, expires_at)"
                " VALUES (?,?,?,?)",
                (self._hash(token), uid, self._now(), expires),
            )
            conn.commit()
        return token

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        now = self._now()
        with self._connect() as conn:
            row = conn.execute(
                """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
                   WHERE s.token_hash = ? AND s.expires_at > ?""",
                (self._hash(token), now),
            ).fetchone()
        return dict(row) if row else None

    def delete_session(self, token: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (self._hash(token),)
            )
            conn.commit()
        return cur.rowcount > 0

    # --- email verification -------------------------------------------
    def create_verification_token(self, uid: int) -> str:
        token = secrets.token_urlsafe(20)
        now = datetime.now(timezone.utc)
        expires = (now + timedelta(hours=VERIFY_TTL_HOURS)).isoformat(
            timespec="seconds"
        )
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM email_verifications WHERE user_id = ?", (uid,)
            )
            conn.execute(
                """INSERT INTO email_verifications (token_hash, user_id, created_at, expires_at)
                   VALUES (?,?,?,?)""",
                (self._hash(token), uid, self._now(), expires),
            )
            conn.commit()
        return token

    def consume_verification_token(self, uid: int, token: str) -> bool:
        now = self._now()
        with self._connect() as conn:
            row = conn.execute(
                """SELECT token_hash FROM email_verifications
                   WHERE user_id = ? AND expires_at > ?""",
                (uid, now),
            ).fetchone()
            if row is None:
                return False
            if not secrets.compare_digest(row["token_hash"], self._hash(token)):
                return False
            conn.execute(
                "DELETE FROM email_verifications WHERE user_id = ?", (uid,)
            )
            conn.execute(
                "UPDATE users SET email_verified = 1 WHERE id = ?", (uid,)
            )
            conn.commit()
        return True

    # --- sync store ----------------------------------------------------
    # Merge rules: rows are keyed per (user, whisky/list); on upsert the
    # larger updated_at wins; the device is authoritative for what it pushes.
    _SYNC_TABLES: Dict[
        str, Tuple[str, List[str], List[str]]
    ] = {
        "favorites": ("sync_favorites", ["user_id", "whisky_id"], ["updated_at"]),
        "scores": ("sync_scores", ["user_id", "whisky_id"], ["score", "updated_at"]),
        "notes": ("sync_notes", ["user_id", "whisky_id"], ["note", "updated_at"]),
        "lists": ("sync_lists", ["user_id", "list_id"], ["name", "default_type", "sort_order", "updated_at"]),
        "items": ("sync_list_items", ["user_id", "list_id", "whisky_id"], ["sort_order", "note", "updated_at"]),
    }

    def sync_push(self, uid: int, kind: str, rows: List[Dict[str, Any]]) -> int:
        """Upsert a batch of rows for one sync table. Later updated_at wins."""
        if kind not in self._SYNC_TABLES:
            raise KeyError(f"unknown sync kind: {kind}")
        table, keys, cols = self._SYNC_TABLES[kind]
        upserted = 0
        with self._connect() as conn:
            for row in rows:
                payload = {k: row.get(k) for k in cols}
                payload.update({k: row.get(k) for k in keys if k != "user_id"})
                payload["user_id"] = uid
                if "updated_at" not in payload or not payload["updated_at"]:
                    payload["updated_at"] = self._now()
                # prefer stored row if its updated_at is newer
                cur = conn.execute(
                    f"SELECT updated_at FROM {table} WHERE "
                    + " AND ".join(f"{k}=?" for k in keys),
                    tuple(payload[k] for k in keys),
                ).fetchone()
                if cur and cur["updated_at"] > payload["updated_at"]:
                    continue  # server copy is newer; keep it
                placeholders = ", ".join("?" * len(payload))
                column_names = ", ".join(payload.keys())
                updatable = [c for c in cols if c != "updated_at"]
                do_update = ", ".join(
                    [f"{c}=excluded.{c}" for c in updatable]
                    + ["updated_at=excluded.updated_at"]
                )
                conn.execute(
                    f"INSERT INTO {table} ({column_names}) VALUES ({placeholders}) "
                    f"ON CONFLICT({', '.join(keys)}) DO UPDATE SET {do_update}",
                    tuple(payload.values()),
                )
                upserted += 1
            conn.commit()
        return upserted

    def sync_pull_all(self, uid: int) -> Dict[str, List[Dict[str, Any]]]:
        result: Dict[str, List[Dict[str, Any]]] = {}
        with self._connect() as conn:
            for kind, (table, _keys, _cols) in self._SYNC_TABLES.items():
                rows = conn.execute(
                    f"SELECT * FROM {table} WHERE user_id = ?", (uid,)
                ).fetchall()
                result[kind] = [
                    {k: r[k] for k in r.keys() if k != "user_id"} for r in rows
                ]
        return result

    def delete_sync_all(self, uid: int) -> None:
        with self._connect() as conn:
            for _kind, (table, _keys, _cols) in self._SYNC_TABLES.items():
                conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (uid,))
            conn.commit()

    def delete_user(self, uid: int) -> bool:
        """Remove a user and all of their data (account closure / KVKK erasure).

        `sessions` and `email_verifications` cascade via FK ON DELETE CASCADE;
        the sync tables have no FK so they are removed explicitly.
        """
        with self._connect() as conn:
            for _kind, (table, _keys, _cols) in self._SYNC_TABLES.items():
                conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM email_verifications WHERE user_id = ?", (uid,))
            cur = conn.execute("DELETE FROM users WHERE id = ?", (uid,))
            conn.commit()
        return cur.rowcount > 0
