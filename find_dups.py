import re

def check_file():
    with open('frontend/lib/core/localization/app_translations.dart', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into tr and en
    tr_match = re.search(r"'tr':\s*{(.*?)}", content, re.DOTALL)
    en_match = re.search(r"'en':\s*{(.*?)}", content, re.DOTALL)
    
    for lang, match in [('tr', tr_match), ('en', en_match)]:
        if match:
            keys = re.findall(r"'([^']+)':\s*'", match.group(1))
            seen = set()
            dups = set()
            for k in keys:
                if k in seen:
                    dups.add(k)
                seen.add(k)
            print(f"Duplicates in {lang}: {dups}")

check_file()
