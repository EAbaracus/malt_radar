"""social/queue.py — Onay kuyruğu + insan GO kapısı (KEP PromotionGate deseni).

Sosyal yayın bir üretim mutasyonudur -> AGENTS.md public kanonik disiplini uygulanır:
  - İçerik staging kuyruğuna yazılır (draft -> ready).
  - Yayından ÖNCE human GO şart (dry-run != apply): herhangi bir platforma
    otomatik yayın YOKTUR. Bu modül yalnız kuyruk durumunu yönetir.
  - GO verilmiş bir post yayınlanmış sayılmaz; gerçek paylaşım insan tarafından
    (veya açıkça onaylanmış bir entegrasyon) yürütülür. Queue burada yalnız
    kayıt/ı̇zleme tutar.

Fark: AGENTS'daki production.db promotion hattından bağımsızdır; bu yayın
kuyruğu ayrı bir JSON dosyasıdır (social/queue_*.json), production.db'ye asla dokunmaz.
"""

from __future__ import annotations

import json as _json
import datetime as _dt
from pathlib import Path as _P

QUEUE_DIR = _P(__file__).resolve().parent / "post_queue_data"


class QueueError(RuntimeError):
    pass


def _default_queue_path() -> _P:
    return QUEUE_DIR / "social_queue.json"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _load(path: str) -> dict:
    p = _P(path)
    if not p.exists():
        return {"created": _now(), "config": {}, "posts": []}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return _json.load(f)
    except (OSError, _json.JSONDecodeError) as e:
        raise QueueError(f"Kuyruk dosyasi okunamadi: {p} ({e})")


def _write(path: str, data: dict) -> None:
    p = _P(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        _json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(p)  # atomic — corruption riski yok


def stage(posts: list, path: str | None = None) -> dict:
    """Taslaklari kuyruga (draft) yazar; yayina cikartmaz."""
    q = _load(path or str(_default_queue_path()))
    by_id = {p["id"]: p for p in q["posts"]}
    added = 0
    for p in posts:
        d = {**(_dic(p) if not isinstance(p, dict) else p)}
        d.setdefault("status", "draft")
        if d["id"] not in by_id:
            by_id[d["id"]] = d
            added += 1
    q["posts"] = list(by_id.values())
    _write(path or str(_default_queue_path()), q)
    return {"added": added, "total": len(q["posts"])}


def _dic(p):
    if isinstance(p, dict):
        return p
    import dataclasses
    if dataclasses.is_dataclass(p):
        return dataclasses.asdict(p)
    return dict(p)


def to_ready(post_ids: list[str], path: str | None = None) -> dict:
    """draft -> ready. HENÜZ GO/apply değil; insan gözümün önüne serilmek içindir."""
    q = _load(path or str(_default_queue_path()))
    moved = 0
    for post in q["posts"]:
        if post["id"] in set(post_ids) and post["status"] == "draft":
            post["status"] = "ready"
            post["ready_utc"] = _now()
            moved += 1
    _write(path or str(_default_queue_path()), q)
    return {"moved_to_ready": moved}


def pending_go(path: str | None = None) -> list:
    """ready durumundaki (human GO bekleyen) postları getirir."""
    q = _load(path or str(_default_queue_path()))
    return [p for p in q["posts"] if p["status"] == "ready"]


def go(post_ids: list[str], approver: str, path: str | None = None) -> dict:
    """İNSAN GO: ready -> approved (yayına hazır kaydı). Otomatik yayın yok."""
    if not post_ids:
        raise QueueError("GO için boş post listesi verildi.")
    q = _load(path or str(_default_queue_path()))
    approved = []
    for post in q["posts"]:
        if post["id"] in set(post_ids) and post["status"] == "ready":
            post["status"] = "approved"
            post["approved_utc"] = _now()
            post["approved_by"] = approver
            approved.append(post["id"])
    _write(path or str(_default_queue_path()), q)
    return {"approved": approved}


def published(post_ids: list[str], path: str | None = None) -> dict:
    """İnsan veya yetkili entegrasyon yayını yaptıktan SONRA kayıt düşer."""
    q = _load(path or str(_default_queue_path()))
    done = []
    for post in q["posts"]:
        if post["id"] in set(post_ids) and post["status"] == "approved":
            post["status"] = "published"
            post["published_utc"] = _now()
            done.append(post["id"])
    _write(path or str(_default_queue_path()), q)
    return {"published": done}


# --- Zamanlama: onaylanan (approved) postlar belirli bir akşam slotuna alınır ---

def schedule(listing: dict, path: str | None = None) -> dict:
    """listing = {post_id: iso_utc} — approved postlara yayın zamanı yazar.

    Yayını tetiklemez; yalnız 'scheduled_utc' alanını set eder. Gerçek yayın
    dispatcher (publish_due) okuyup insan/entegrasyon tarafından yürütülür.
    """
    q = _load(path or str(_default_queue_path()))
    ids = set(listing)
    for post in q["posts"]:
        if post["id"] in ids and post["status"] == "approved":
            post["scheduled_utc"] = listing[post["id"]]
    _write(path or str(_default_queue_path()), q)
    return {"scheduled": len(ids)}


def publish_due(path: str | None = None, now_utc: str | None = None,
                lang: str | None = None, limit: int | None = None) -> list:
    """Return due approved posts, optionally filtered by language and capped.

    Legacy posts without ``lang`` are TR. A cron slot must pass its language
    explicitly and a limit of one; otherwise a missed slot can publish an old
    backlog or consume an EN slot with a TR post.
    """
    q = _load(path or str(_default_queue_path()))
    now = now_utc or _now()
    due = []
    for post in q["posts"]:
        if post["status"] != "approved" or not post.get("scheduled_utc"):
            continue
        if post["scheduled_utc"] > now:
            continue
        if lang is not None and post.get("lang", "tr") != lang:
            continue
        due.append(post)
    due.sort(key=lambda post: post.get("scheduled_utc", ""))
    return due[:limit] if limit is not None else due


def status(path: str | None = None) -> dict:
    q = _load(path or str(_default_queue_path()))
    from collections import Counter
    return {"total": len(q["posts"]), "by_status": dict(Counter(p["status"] for p in q["posts"]))}


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(_json.dumps(status(), ensure_ascii=False, indent=2))
    elif cmd == "pending":
        for p in pending_go():
            print(p["id"], "|", p["platform"], "|", p["body"][:80])
    else:
        print("usage: queue.py [status|pending]")
