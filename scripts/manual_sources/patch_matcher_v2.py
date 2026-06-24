from pathlib import Path
import re

path = Path("scripts/manual_sources/match_notebooklm_profiles_to_production.py")
text = path.read_text(encoding="utf-8")

# Patch norm()
old_norm = '''def norm(s):
    if s is None:
        return ""
    s = str(s).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\\b(the|distillery|single|malt|whisky|whiskey|year|years|old|yo)\\b", " ", s)
    s = re.sub(r"\\s+", " ", s).strip()
    return s
'''

new_norm = '''def norm(s):
    if s is None:
        return ""
    s = str(s).lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\\b(\\d+)\\s*year\\s*old\\b", r"\\1", s)
    s = re.sub(r"\\b(\\d+)\\s*years\\s*old\\b", r"\\1", s)
    s = re.sub(r"\\b(\\d+)\\s*yo\\b", r"\\1", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\\b(the|distillery|single|malt|whisky|whiskey|year|years|old|yo)\\b", " ", s)
    s = re.sub(r"\\s+", " ", s).strip()
    return s
'''

if old_norm not in text:
    raise SystemExit("norm() eski hali bulunamadı; dosya beklenen formatta değil.")
text = text.replace(old_norm, new_norm)

# Patch gate()
text = re.sub(
    r'def gate\(best, second\):\n    if not best:\n        return "NO_MATCH"\n\n    score = best\["score"\]\n    margin = score - second\["score"\] if second else score\n\n    if score >= 0\.92 and margin >= 0\.03:\n        return "HIGH"\n    if score >= 0\.84 and margin >= 0\.02:\n        return "REVIEW"\n    return "NO_MATCH"',
    '''def gate(best, second):
    if not best:
        return "NO_MATCH"

    score = best["score"]
    margin = score - second["score"] if second else score
    name_score = best.get("name_score", 0)
    distillery_score = best.get("distillery_score", 0)

    if name_score >= 0.97 and margin >= 0.05:
        return "HIGH"

    if name_score >= 0.94 and distillery_score >= 0.70 and margin >= 0.03:
        return "HIGH"

    if score >= 0.92 and margin >= 0.03:
        return "HIGH"

    if score >= 0.80 and margin >= 0.02:
        return "REVIEW"

    return "NO_MATCH"''',
    text,
)

path.write_text(text, encoding="utf-8")
print("patched:", path)
