import os
import re

def find_duplicate_i18n_keys():
    app_translations_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "frontend", "lib", "core", "localization", "app_translations.dart"
    )
    
    with open(app_translations_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tr_match = re.search(r"'tr':\s*{(.*?)}", content, re.DOTALL)
    en_match = re.search(r"'en':\s*{(.*?)}", content, re.DOTALL)
    
    all_dups = {}
    for lang, match in [('tr', tr_match), ('en', en_match)]:
        if match:
            # We look for lines like 'key': 'value'
            keys = re.findall(r"'([^']+)':\s*'", match.group(1))
            seen = set()
            dups = set()
            for k in keys:
                if k in seen:
                    dups.add(k)
                seen.add(k)
            if dups:
                all_dups[lang] = list(dups)
    return all_dups

def test_i18n_has_no_duplicate_keys():
    dups = find_duplicate_i18n_keys()
    assert len(dups) == 0, f"Duplicate i18n keys found: {dups}"
