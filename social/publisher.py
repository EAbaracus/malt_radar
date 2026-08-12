"""social/publisher.py — Yayın katmanı (X API v2'ye bağlanabilir, fail-closed).

Batch GO modeli: insan onayı sonrası onaylanan postlar zamanlanır; zamanı
gelince bu modül X API v2'ye gönderir. GERÇEK gönderim için şunlar gerekir:
  - X Developer App (X Developer portal) → API key+secret (Read+Write).
  - OAuth 1.0a user access token + secret, maltradar@gmail.com hesabına bağlı.
Kimlikler SECRET'lerdir: .env içinde tutulur, asla git'e ve asla debug'a yazılmaz.

Kritik sınır korunur:
  - Kimlik yoksa veya Yetki yoksa -> fail-closed: yayın YAYINLANMAZ, çıktı dosyası
    + QueueError fırlatır. SAHTE 'published' İŞARETİ ASLA VERİLMEZ.
  - Ortam değişkenleri: MALT_RADAR_X_API_KEY, MALT_RADAR_X_API_SECRET,
    MALT_RADAR_X_ACCESS_TOKEN, MALT_RADAR_X_ACCESS_SECRET.
"""

from __future__ import annotations

import json as _json
import datetime as _dt
import os as _os
from pathlib import Path as _P
from social import queue as _queue

OUT_DIR = _P(__file__).resolve().parent / "outgoing"

# X API v2 endpoint — user-context OAuth 1.0a
_X_POST_ENDPOINT = "https://api.x.com/2/tweets"


class PublishError(RuntimeError):
    pass


def load_env(path: str | None = None) -> None:
    """`.env` dosyasını os.environ'a yükler (varsa). Secret'lar diskten okunur.

    Varsayılan yol: social/.env. Yoksa sessizce geçer — kimlikler başka yoldan
    (gerçek ortam değişkenleri) sağlanmış olabilir. İçeriği asla yazdırmaz.
    """
    from pathlib import Path as _P2
    p = _P2(path) if path else _P(__file__).resolve().parent / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in _os.environ:
            _os.environ[k] = v


def x_credentials_present() -> bool:
    """Tüm X API kimlikleri yapılandırılmış mı? (tek eksik bile => Fail)"""
    return all(_os.environ.get(k) for k in (
        "MALT_RADAR_X_API_KEY", "MALT_RADAR_X_API_SECRET",
        "MALT_RADAR_X_ACCESS_TOKEN", "MALT_RADAR_X_ACCESS_SECRET",
    ))


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def render_outgoing(due_posts: list[dict]) -> str:
    lines = []
    for p in due_posts:
        lines.append("#" * 60)
        lines.append(f"id: {p['id']}")
        lines.append(f"handle: {p['handle']}  platform: {p['platform']}  tpl: {p['template']}")
        lines.append(f"source_sha256: {p.get('source_sha256','')}")
        lines.append("-" * 60)
        lines.append(p["body"])
        lines.append("")
    return "\n".join(lines)


def _urlescape(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(str(s), safe="-._~")


def _oauth1_signature(method, url, oauth_params: list, consumer_secret: str,
                      token_secret: str) -> str:
    """OAuth 1.0a HMAC-SHA1 imzası — saf, deterministic (test edilebilir).

    oauth_params: [(key,value),...] — imzaya katilacak TUM parametreler
    (oauth_* + body parametreleri, orn 'text'). Siralama + %-encoding burada
    yapilir. _oauth1_header body'den 'text'i cikarip bu listeye ekler.
    """
    import base64, hashlib, hmac

    params = sorted(oauth_params)
    base = _urlescape(method.upper()) + "&" + _urlescape(url) + "&" + _urlescape(
        "&".join(f"{k}={_urlescape(v)}" for k, v in params))
    key = _urlescape(consumer_secret) + "&" + _urlescape(token_secret)
    return base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()


def _oauth1_header(method, url, body: bytes) -> dict:
    """OAuth 1.0a %-imzalı Authorization header (HMAC-SHA1).

    Sadece uygun secret'lar mevcutken çağrılır; eksikse PublishError.
    """
    import base64

    missing = [k for k in ("MALT_RADAR_X_API_KEY", "MALT_RADAR_X_API_SECRET",
                           "MALT_RADAR_X_ACCESS_TOKEN", "MALT_RADAR_X_ACCESS_SECRET")
               if not _os.environ.get(k)]
    if missing:
        raise PublishError(f"X kimlikleri eksik: {missing}")

    oauth_consumer_key = _os.environ["MALT_RADAR_X_API_KEY"]
    oauth_consumer_secret = _os.environ["MALT_RADAR_X_API_SECRET"]
    oauth_token = _os.environ["MALT_RADAR_X_ACCESS_TOKEN"]
    oauth_token_secret = _os.environ["MALT_RADAR_X_ACCESS_SECRET"]

    oauth_nonce = base64.b64encode(_os.urandom(16)).decode().rstrip("=")
    oauth_timestamp = str(int(_dt.datetime.now().timestamp()))

    oauth_params = [
        ("oauth_consumer_key", oauth_consumer_key),
        ("oauth_nonce", oauth_nonce),
        ("oauth_signature_method", "HMAC-SHA1"),
        ("oauth_timestamp", oauth_timestamp),
        ("oauth_token", oauth_token),
        ("oauth_version", "1.0"),
    ]
    # API v2 JSON body OAuth 1.0a imza base string'ine DAHIL EDILMEZ.
    # Yalnız application/x-www-form-urlencoded body parametreleri imzaya girer.
    # JSON body'den 'text' eklemek base string'i bozar -> X 401 döner.
    sig = _oauth1_signature(method, url, oauth_params, oauth_consumer_secret,
                            oauth_token_secret)
    header_params = oauth_params + [("oauth_signature", sig)]
    header = "OAuth " + ", ".join(
        f'{k}="{_urlescape(v)}"' for k, v in header_params)
    return {"Authorization": header}


def apply_post(post: dict, qpath: str | None = None, dry_run: bool = False) -> dict:
    """Onaylı+zamanı gelmiş postu X API v2'ye gönderir; başarılıysa 'published'.

    dry_run=True: gerçek istek atmaz, imza denemesini + body'yi raporlar.
    Kimlik yoksa fail-closed: yayın yok, sahte published yok.
    Bu fonksiyon yalnız platform=='x' postlarına uygundur; başka platform
    şimdilik desteklenmez (PublishError).
    """
    if post.get("platform", "x") != "x":
        raise PublishError(f"Platform '{post.get('platform')}' henüz desteklenmiyor (yalnız x).")

    if not x_credentials_present():
        raise PublishError("X API kimlikleri yapılandırılmamış (fail-closed; yayın yok).")

    body = _json.dumps({"text": post["body"]}).encode()

    if dry_run:
        try:
            headers = _oauth1_header("POST", _X_POST_ENDPOINT, body)
            return {"dry_run": True, "authorization_ready": bool(headers["Authorization"]),
                    "will_send_to": _X_POST_ENDPOINT}
        except PublishError as e:
            return {"dry_run": True, "error": str(e)}

    import requests
    try:
        headers = {"Content-Type": "application/json", **_oauth1_header("POST", _X_POST_ENDPOINT, body)}
        resp = requests.post(_X_POST_ENDPOINT, data=body, headers=headers, timeout=30)
    except PublishError as e:
        raise PublishError(str(e))  # imza hatası
    except Exception as e:  # network/timeout
        raise PublishError(f"X istegi basarisiz (id={post['id']}): {e}")

    if resp.status_code not in (200, 201):
        raise PublishError(f"X API hata {resp.status_code} (id={post['id']}): {resp.text[:200]}")

    # Başarılı: ancak şimdi 'published'
    _queue.published([post["id"]], path=qpath)
    return {"tweet_id": resp.json().get("data", {}).get("id"), "marked_published": [post["id"]]}


def dump_outgoing(qpath: str | None = None, now_utc: str | None = None) -> dict:
    """Zamanı gelmiş onaylı postları tek bir çıktı dosyasına döker (elle paylaşım için).

    Queue statüsünü 'published'a ÇEKMEZ — insan gerçekten paylaştıktan sonra
    `apply_post` / queue.published çağrılır. Bu, sahte onay izini önler.
    """
    due = _queue.publish_due(path=qpath, now_utc=now_utc)
    if not due:
        return {"due": 0, "file": None}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = OUT_DIR / f"outgoing_{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(render_outgoing(due))
    return {"due": len(due), "file": str(fname)}


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dump"
    if cmd == "dump":
        print(_json.dumps(dump_outgoing(), ensure_ascii=False, indent=2))
    elif cmd == "creds":
        print("X kimlikleri mevcut:" , x_credentials_present())
    else:
        print(f"usage: publisher.py [dump|creds]  (gercek gonderim: apply_post X API v2 + .env kimlikleri)")

