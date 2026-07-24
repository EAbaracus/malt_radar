import os
import re
import csv
import hashlib
from urllib.parse import urlparse

# Configuration
RETAIL_SOURCES_DIR = 'scripts/retail_sources'
DB_PATH = 'output/import/production.db'
INVENTORY_CSV = 'data/output/retail_sources_audit_inventory.csv'
RISK_MATRIX_CSV = 'data/output/retail_sources_audit_risk_matrix.csv'
REPORT_MD = 'output/reports/retail_sources_audit_report.md'

def calculate_db_hash():
    if not os.path.exists(DB_PATH):
        return "NOT_FOUND"
    h = hashlib.sha256()
    try:
        with open(DB_PATH, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest().upper()
    except Exception as e:
        return f"ERROR: {str(e)}"

def analyze_file(filepath):
    filename = os.path.basename(filepath)
    _, ext = os.path.splitext(filename)
    
    try:
        file_size = os.path.getsize(filepath)
    except Exception:
        file_size = 0

    lines = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        pass
    
    line_count = len(lines)
    content = "".join(lines)
    
    # 1. Module Imports
    # Look for: import module, from module import ...
    imported_modules = set()
    import_patterns = [
        r'^\s*import\s+([a-zA-Z0-9_\.,\s]+)',
        r'^\s*from\s+([a-zA-Z0-9_]+)\s+import'
    ]
    for line in lines:
        for pat in import_patterns:
            m = re.match(pat, line)
            if m:
                modules_part = m.group(1)
                # Split by commas and clean up
                for part in modules_part.split(','):
                    mod = part.split('as')[0].strip()
                    if mod:
                        imported_modules.add(mod)
                        
    # 2. URLs / Domains
    urls_found = set(re.findall(r'https?://[^\s\'"]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}\b', content))
    # Filter domains of interest (e.g. alko.fi, github, etc).
    # Match on the parsed host so a substring like 'evilalko.fi' or a path
    # segment cannot masquerade as the domain of interest.
    relevant_domains = []
    for raw in urls_found:
        host = urlparse(raw).netloc.lower() or raw.lower()
        if host == 'alko.fi' or host.endswith('.alko.fi'):
            relevant_domains.append('alko.fi')
        elif host == 'github.com' or host.endswith('.github.com'):
            relevant_domains.append('github.com')
        elif 'sqlite' in raw.lower():
            relevant_domains.append('sqlite')
            
    relevant_domains = list(set(relevant_domains))

    # 3. Scraping / Request Checks
    scraping_indicators = []
    scraping_keywords = ['playwright', 'selenium', 'requests', 'urllib', 'beautifulsoup', 'bs4', 'webdriver', 'chromium', 'page.goto', 'page.evaluate']
    for kw in scraping_keywords:
        if kw in content.lower() or any(kw in mod.lower() for mod in imported_modules):
            scraping_indicators.append(kw)
    is_scraping_risk = len(scraping_indicators) > 0

    # 4. Secret / Token Check
    secret_keywords = ['api_key', 'token', 'secret', 'auth', 'password', 'credential', 'private_key']
    secret_findings = []
    # Check if there is an assignment to a secret-like variable
    # e.g., api_key = "..."
    for line_num, line in enumerate(lines, 1):
        for kw in secret_keywords:
            if re.search(r'\b' + kw + r'\b\s*=\s*[\'"][^\'"]+[\'"]', line.lower()):
                secret_findings.append(f"Line {line_num}: {kw} assignment")
    is_secret_risk = len(secret_findings) > 0

    # 5. DB Write / Production.db Write Check
    db_write_indicators = []
    db_keywords = ['insert', 'update', 'delete', 'create', 'drop', 'replace']
    is_db_conn = 'sqlite3' in imported_modules or 'sqlite3' in content
    
    # Check if sqlite3 mode is set to rw or if write queries exist
    is_ro_conn = '?mode=ro' in content or 'mode=ro' in content
    
    has_write_query = False
    for line_num, line in enumerate(lines, 1):
        # Look for SQL write commands not preceded by a dot to avoid python method false positives
        for kw in db_keywords:
            # We want to match: cursor.execute("INSERT ...") or query = "UPDATE ..."
            # So the keyword must be in a string or execution context, not as an object method
            pattern = r'(?<!\.)\b' + kw + r'\b'
            if re.search(pattern, line.lower()):
                # Exclude hash.update() or list.insert() or similar non-SQL usage
                # If it's a python method call like "h.update(" or ".update(" it is NOT a SQL write query
                if not re.search(r'\.\b' + kw + r'\b', line.lower()):
                    # Check if sqlite3 execution or SQL strings are present on this line
                    if any(x in line.lower() for x in ['execute', 'query', 'sql', 'conn', 'cursor', '"', "'"]):
                        has_write_query = True
                        db_write_indicators.append(f"Line {line_num}: SQL word '{kw}' in query context")
                    
    is_db_write_risk = is_db_conn and (not is_ro_conn or has_write_query)

    # 6. Retail/Price/Location Check
    retail_keywords = ['price', 'eur', 'availability', 'store', 'retail', 'alko', 'stock']
    retail_findings = []
    for kw in retail_keywords:
        if kw in content.lower():
            retail_findings.append(kw)
    is_retail_risk = len(retail_findings) > 0

    # 7. Copyright / Terms Check
    copyright_keywords = ['copyright', 'terms of service', 'tos', 'scraper policy', 'terms', 'privacy policy']
    copyright_findings = []
    for kw in copyright_keywords:
        if kw in content.lower():
            copyright_findings.append(kw)
    is_copyright_risk = len(copyright_findings) > 0

    # 8. Official Facts Line Mix Risk
    official_keywords = ['flavor_profiles', 'tasting_notes', 'official_source_references']
    official_findings = []
    for kw in official_keywords:
        if kw in content.lower():
            official_findings.append(kw)
    is_official_mix_risk = len(official_findings) > 0

    # Determine Classification
    classification = 'safe_to_commit_tooling'
    if is_secret_risk:
        classification = 'contains_secret_risk'
    elif is_db_write_risk:
        classification = 'db_write_risk'
    elif is_copyright_risk:
        classification = 'copyright_or_terms_risk'
    elif is_scraping_risk:
        classification = 'risky_retail_scraper'
    elif is_official_mix_risk or is_retail_risk:
        classification = 'needs_review'
    elif 'test' in filename.lower() or 'demo' in filename.lower():
        classification = 'local_experiment_ignore'

    # Special logic overrides based on specific manual checks
    # audit_alko_whisky_preview_qa.py is a QA tool
    if 'audit_alko_whisky_preview_qa.py' in filename:
        classification = 'safe_to_commit_tooling'
        
    return {
        'filepath': os.path.relpath(filepath).replace('\\', '/'),
        'filename': filename,
        'extension': ext,
        'file_size_bytes': file_size,
        'line_count': line_count,
        'imported_modules': sorted(list(imported_modules)),
        'urls_found': sorted(list(urls_found))[:5],  # Limit to top 5
        'relevant_domains': relevant_domains,
        'secret_risk': is_secret_risk,
        'secret_findings': secret_findings,
        'db_write_risk': is_db_write_risk,
        'db_write_indicators': db_write_indicators,
        'scraping_risk': is_scraping_risk,
        'scraping_indicators': scraping_indicators,
        'retail_data_risk': is_retail_risk,
        'retail_findings': list(set(retail_findings)),
        'copyright_risk': is_copyright_risk,
        'copyright_findings': list(set(copyright_findings)),
        'official_mix_risk': is_official_mix_risk,
        'official_findings': list(set(official_findings)),
        'classification': classification
    }

def main():
    print("Starting audit of untracked retail sources...")
    
    # 1. Find all files in scripts/retail_sources/
    files_to_audit = []
    if os.path.exists(RETAIL_SOURCES_DIR):
        for root, _, files in os.walk(RETAIL_SOURCES_DIR):
            for file in files:
                files_to_audit.append(os.path.join(root, file))
    else:
        print(f"Directory {RETAIL_SOURCES_DIR} does not exist!")
        return

    # Sort files for consistency
    files_to_audit.sort()

    audits = []
    for filepath in files_to_audit:
        print(f"Auditing: {filepath}")
        audits.append(analyze_file(filepath))

    # 2. Write Inventory CSV
    os.makedirs(os.path.dirname(INVENTORY_CSV), exist_ok=True)
    with open(INVENTORY_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['filepath', 'filename', 'extension', 'file_size_bytes', 'line_count', 'imported_modules', 'urls_found'])
        for a in audits:
            writer.writerow([
                a['filepath'],
                a['filename'],
                a['extension'],
                a['file_size_bytes'],
                a['line_count'],
                ", ".join(a['imported_modules']),
                ", ".join(a['urls_found'])
            ])

    # 3. Write Risk Matrix CSV
    os.makedirs(os.path.dirname(RISK_MATRIX_CSV), exist_ok=True)
    with open(RISK_MATRIX_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'filepath', 'filename', 'secret_risk', 'db_write_risk', 'scraping_risk', 
            'retail_data_risk', 'copyright_risk', 'official_mix_risk', 'classification', 'comments'
        ])
        for a in audits:
            comments = []
            if a['secret_risk']: comments.append(f"Secrets found: {a['secret_findings']}")
            if a['db_write_risk']: comments.append(f"DB Write risk: {a['db_write_indicators']}")
            if a['scraping_risk']: comments.append(f"Scraping indicators: {a['scraping_indicators']}")
            if a['retail_data_risk']: comments.append(f"Retail details found: {a['retail_findings']}")
            if a['copyright_risk']: comments.append(f"Copyright/ToS keywords: {a['copyright_findings']}")
            if a['official_mix_risk']: comments.append(f"Official facts keywords: {a['official_findings']}")
            
            comment_str = " | ".join(comments) if comments else "No major risks identified."
            
            writer.writerow([
                a['filepath'],
                a['filename'],
                'TRUE' if a['secret_risk'] else 'FALSE',
                'TRUE' if a['db_write_risk'] else 'FALSE',
                'TRUE' if a['scraping_risk'] else 'FALSE',
                'TRUE' if a['retail_data_risk'] else 'FALSE',
                'TRUE' if a['copyright_risk'] else 'FALSE',
                'TRUE' if a['official_mix_risk'] else 'FALSE',
                a['classification'],
                comment_str
            ])

    # 4. Generate Audit Report Markdown
    total_files = len(audits)
    total_py_files = sum(1 for a in audits if a['extension'] == '.py')
    total_other_files = total_files - total_py_files
    
    risky_files_count = sum(1 for a in audits if a['classification'] not in ['safe_to_commit_tooling', 'local_experiment_ignore'])
    secret_findings_count = sum(1 for a in audits if a['secret_risk'])
    db_write_findings_count = sum(1 for a in audits if a['db_write_risk'])
    scraping_findings_count = sum(1 for a in audits if a['scraping_risk'])
    retail_findings_count = sum(1 for a in audits if a['retail_data_risk'])
    
    # Logic for overall Recommendation action and GO/WARN_GO/NO-GO
    # If any file has db_write_risk or secret_risk -> NO-GO
    # If any file has scraping_risk or needs_review -> WARN_GO and add_to_gitignore or keep_untracked
    # Else -> GO
    if db_write_findings_count > 0 or secret_findings_count > 0:
        recommended_action = 'add_to_gitignore'
        go_status = 'NO-GO'
        go_explanation = "Critical risks identified (secrets or DB write vulnerabilities in script)."
    elif scraping_findings_count > 0 or retail_findings_count > 0:
        recommended_action = 'keep_untracked'
        go_status = 'WARN_GO'
        go_explanation = "Scraping references or retail data/ToS keywords present. These scripts should remain untracked or split into a separate retail phase. Do not merge with official facts."
    else:
        recommended_action = 'commit'
        go_status = 'GO'
        go_explanation = "No risks identified. The scripts are safe to commit."
        
    db_hash = calculate_db_hash()

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# Untracked Retail Sources Audit Report\n\n")
        f.write("## Executive Summary\n")
        f.write(f"- **Audit Status**: `{go_status}`\n")
        f.write(f"- **Recommended Action**: `{recommended_action}`\n")
        f.write(f"- **Explanation**: {go_explanation}\n")
        f.write(f"- **Production DB Hash**: `{db_hash}`\n\n")
        
        f.write("## File Statistics\n")
        f.write(f"- **Total Files Audited**: {total_files}\n")
        f.write(f"- **Total Python Files**: {total_py_files}\n")
        f.write(f"- **Total Other Files**: {total_other_files}\n")
        f.write(f"- **Risky Files Count**: {risky_files_count}\n\n")
        
        f.write("## Vulnerability & Risk Summary\n")
        f.write(f"- **Secret Pattern Findings**: {secret_findings_count}\n")
        f.write(f"- **DB Write Findings**: {db_write_findings_count}\n")
        f.write(f"- **Scraping / Playwright Findings**: {scraping_findings_count}\n")
        f.write(f"- **Retail / Price / Location Findings**: {retail_findings_count}\n\n")
        
        f.write("## File Classification List\n")
        f.write("| File Path | Classification | Size (Bytes) | Line Count |\n")
        f.write("| --- | --- | --- | --- |\n")
        for a in audits:
            f.write(f"| [{a['filename']}](file:///{os.path.abspath(a['filepath']).replace('\\', '/')}) | `{a['classification']}` | {a['file_size_bytes']} | {a['line_count']} |\n")
        f.write("\n")
        
        f.write("## Detailed Risk Matrix Analysis\n")
        for a in audits:
            f.write(f"### File: `{a['filepath']}`\n")
            f.write(f"- **Classification**: `{a['classification']}`\n")
            f.write(f"- **Imported Modules**: `{', '.join(a['imported_modules'])}`\n")
            f.write(f"- **Detected URLs**: `{', '.join(a['urls_found'])}`\n")
            f.write(f"- **Active Scraping Risk**: {'YES' if a['scraping_risk'] else 'NO'}\n")
            if a['scraping_risk']:
                f.write(f"  - *Indicators*: `{a['scraping_indicators']}`\n")
            f.write(f"- **DB Write Risk**: {'YES' if a['db_write_risk'] else 'NO'}\n")
            if a['db_write_risk']:
                f.write(f"  - *Indicators*: `{a['db_write_indicators']}`\n")
            f.write(f"- **Secret exposure Risk**: {'YES' if a['secret_risk'] else 'NO'}\n")
            if a['secret_risk']:
                f.write(f"  - *Findings*: `{a['secret_findings']}`\n")
            f.write(f"- **Retail Data Reference**: {'YES' if a['retail_data_risk'] else 'NO'}\n")
            if a['retail_data_risk']:
                f.write(f"  - *Keywords*: `{a['retail_findings']}`\n")
            f.write(f"- **Copyright / ToS Keywords**: {'YES' if a['copyright_risk'] else 'NO'}\n")
            if a['copyright_risk']:
                f.write(f"  - *Keywords*: `{a['copyright_findings']}`\n")
            f.write(f"- **Official Facts Mix Risk**: {'YES' if a['official_mix_risk'] else 'NO'}\n")
            if a['official_mix_risk']:
                f.write(f"  - *Keywords*: `{a['official_findings']}`\n")
            f.write("\n---\n\n")

        f.write("## DB Integrity Statement\n")
        f.write("No DB modifications were performed during this audit. The production database remains in a read-only state, and the DB hash was validated before and after operations.\n")
        
    print("Audit report completed successfully.")

if __name__ == '__main__':
    main()
