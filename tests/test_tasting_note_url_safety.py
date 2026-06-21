import sys
import os
import pytest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "tasting_notes"))
import url_safety

def test_exact_domain_accept():
    assert url_safety.is_allowed_web_tasting_note_url("https://masterofmalt.com/path", {"masterofmalt.com"}) == True

def test_www_subdomain_accept():
    assert url_safety.is_allowed_web_tasting_note_url("https://www.masterofmalt.com/path", {"masterofmalt.com"}) == True

def test_nested_valid_subdomain_accept():
    assert url_safety.is_allowed_web_tasting_note_url("https://blog.masterofmalt.com/path", {"masterofmalt.com"}) == True

def test_query_substring_attack_reject():
    assert url_safety.is_allowed_web_tasting_note_url("https://evil.com/?q=masterofmalt.com", {"masterofmalt.com"}) == False

def test_suffix_attack_reject():
    assert url_safety.is_allowed_web_tasting_note_url("https://masterofmalt.com.evil.com/path", {"masterofmalt.com"}) == False

def test_prefix_attack_reject():
    assert url_safety.is_allowed_web_tasting_note_url("https://evil-masterofmalt.com/path", {"masterofmalt.com"}) == False

def test_non_http_scheme_reject():
    assert url_safety.is_allowed_web_tasting_note_url("javascript:alert(1)", {"masterofmalt.com"}) == False
    assert url_safety.is_allowed_web_tasting_note_url("file:///etc/passwd", {"masterofmalt.com"}) == False

def test_empty_malformed_url_reject():
    assert url_safety.is_allowed_web_tasting_note_url("", {"masterofmalt.com"}) == False
    assert url_safety.is_allowed_web_tasting_note_url("not_a_url", {"masterofmalt.com"}) == False

def test_userinfo_spoof_reject():
    assert url_safety.is_allowed_web_tasting_note_url("https://user@masterofmalt.com.evil.com/path", {"masterofmalt.com"}) == False
    assert url_safety.is_allowed_web_tasting_note_url("https://user:pass@masterofmalt.com", {"masterofmalt.com"}) == False

def test_query_domain_bypass():
    # evil.com/?q=masterofmalt.com should be rejected, already tested above.
    pass

def test_query_not_in_match_text():
    # masterofmalt.com/path?q=evil should be accepted, but match text should NOT include 'evil'
    assert url_safety.is_allowed_web_tasting_note_url("https://masterofmalt.com/path?q=evil", {"masterofmalt.com"}) == True
    match_text = url_safety.url_match_text("https://masterofmalt.com/path?q=evil")
    assert "evil" not in match_text
    assert match_text == "masterofmalt.com /path"

def test_url_match_text_extracts_host_and_path():
    assert url_safety.url_match_text("https://www.masterofmalt.com/whiskies/laphroaig-10?query=123#fragment") == "www.masterofmalt.com /whiskies/laphroaig-10"
