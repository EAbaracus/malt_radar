import os
import re

def main():
    target_file = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'lib', 'core', 'localization', 'app_translations.dart')
    report_file = os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'reports', '253_duplicate_project_files_report.md')
    
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    if not os.path.exists(target_file):
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Duplicate Localization Keys\n\nTarget file not found.")
        return
        
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    tr_match = re.search(r"'tr':\s*{(.*?)}", content, re.DOTALL)
    en_match = re.search(r"'en':\s*{(.*?)}", content, re.DOTALL)
    
    lines = ["# Duplicate Project Files Report\n"]
    lines.append("## Localization Key Duplicates\n")
    
    for lang, match in [('tr', tr_match), ('en', en_match)]:
        lines.append(f"### {lang.upper()}\n")
        if match:
            keys = re.findall(r"'([^']+)':\s*'", match.group(1))
            seen = set()
            dups = set()
            for k in keys:
                if k in seen:
                    dups.add(k)
                seen.add(k)
            
            if dups:
                for d in dups:
                    lines.append(f"- `{d}`\n")
            else:
                lines.append("- No duplicates found.\n")
        else:
            lines.append("- Section not found.\n")
        lines.append("\n")
        
    with open(report_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
    print("Report generated successfully.")

if __name__ == '__main__':
    main()
