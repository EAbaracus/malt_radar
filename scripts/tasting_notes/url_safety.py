import urllib.parse

def normalize_hostname(url: str) -> str | None:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return None
        if parsed.username or parsed.password:
            return None
        if not parsed.hostname:
            return None
        return parsed.hostname.lower()
    except Exception:
        return None

def is_allowed_web_tasting_note_url(url: str, allowed_domains: set[str]) -> bool:
    host = normalize_hostname(url)
    if not host:
        return False
    for domain in allowed_domains:
        domain = domain.lower()
        if host == domain or host.endswith('.' + domain):
            return True
    return False

def url_match_text(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()
        return f"{host} {path}"
    except Exception:
        return ""
