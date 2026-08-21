import os
import sys
import argparse
import subprocess
import shlex
import re
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Kurallar ve Sabitler
ALLOWED_DIRS = ['backend/app', 'backend/tests', 'tests', 'etl']
FORBIDDEN_DIRS = ['.git', 'node_modules', '.venv', 'venv', 'build', 'output/import', 'data/input', 'data/output']
FORBIDDEN_FILES = ['.env', 'output/production.db']

def run_command(cmd, cwd=None, capture_output=True):
    """Komutu çalıştırır ve çıktıyı döndürür."""
    try:
        if isinstance(cmd, str):
            cmd = shlex.split(cmd)
        result = subprocess.run(cmd, shell=False, capture_output=capture_output, text=True, cwd=cwd)
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return -1, str(e)

def run_test_agent():
    """python test_agent.py --once komutunu çalıştırır."""
    print(">>> test_agent.py çalıştırılıyor...")
    return run_command("python test_agent.py --once")

def run_pytest():
    """python -m pytest komutunu çalıştırır."""
    print(">>> python -m pytest çalıştırılıyor...")
    return run_command("python -m pytest")

def read_failure_report():
    """hata_analizi.md ve varsa önceki logları okur."""
    report_content = ""
    if os.path.exists("hata_analizi.md"):
        with open("hata_analizi.md", "r", encoding="utf-8") as f:
            report_content += f.read()
            
    old_log = "output/filestructure/30_test_agent_pythonpath_fix_results.txt"
    if os.path.exists(old_log):
        with open(old_log, "r", encoding="utf-8") as f:
            report_content += "\n\n--- 30_test_agent_pythonpath_fix_results.txt ---\n" + f.read()
            
    return report_content

def parse_failed_tests(output_text):
    """Pytest çıktısından ve hata analizinden kırılan testleri parse eder."""
    live_failed_tests = []
    historical_failed_tests = []
    
    # Canlı çıktıdan parse
    lines = output_text.splitlines()
    for line in lines:
        if "FAILED " in line or "ERROR collecting " in line:
            test_name = line.strip()
            if test_name not in live_failed_tests:
                live_failed_tests.append(test_name)
                
    # Hata analizinden parse
    if os.path.exists("hata_analizi.md"):
        with open("hata_analizi.md", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("* ____________ ERROR collecting") or line.startswith("* FAILED"):
                    test_name = line.replace("* ____________ ERROR collecting ", "").replace(" ____________", "").strip()
                    if test_name not in historical_failed_tests:
                        historical_failed_tests.append(test_name)
                        
    return live_failed_tests, historical_failed_tests

def classify_failures(failed_tests, output_text):
    """Test hatalarını sınıflandırır."""
    classifications = []
    for test in failed_tests:
        category = "Bilinmeyen Hata"
        root_cause = "Bilinmiyor"
        risk = "HIGH"
        file_to_modify = None
        
        # Dosya yolunu test isminden bulmaya çalış
        match = re.search(r'(backend/tests/[^\s]+|tests/[^\s]+)', test)
        if match:
            file_to_modify = match.group(1).split("::")[0].strip("_ ")
            
        if "ModuleNotFoundError" in output_text and "No module named 'app'" in output_text:
            category = "Import/PYTHONPATH problemi"
            root_cause = "backend modülleri (app) bulunamıyor. sys.path eksik olabilir."
            risk = "LOW"
        elif "AssertionError" in output_text:
            category = "API kontrat uyumsuzluğu veya Gerçek backend bug"
            root_cause = "Beklenen sonuç ile dönen sonuç uyuşmuyor."
            risk = "MEDIUM"
        elif "Fixture" in output_text or "fixture" in output_text:
            category = "Test fixture/env problemi"
            root_cause = "Eksik veya hatalı test fixture konfigürasyonu."
            risk = "MEDIUM"
            
        classifications.append({
            "test": test,
            "category": category,
            "root_cause": root_cause,
            "risk": risk,
            "file_to_modify": file_to_modify
        })
    return classifications

def create_repair_plan(classifications, pytest_output, test_agent_output, is_live_pass):
    """Onarım planını markdown formatında oluşturur."""
    os.makedirs("output/filestructure", exist_ok=True)
    plan_path = "output/filestructure/32_repair_agent_plan.md"
    
    diff_analysis = ""
    if pytest_output != test_agent_output:
        diff_analysis = (
            "## Çelişkili Test Sonucu Kontrolü\n"
            "- `python -m pytest` ile `python test_agent.py --once` çıktıları farklı!\n"
            "- `test_agent.py` PYTHONPATH'i otomatik ayarlıyor olabilir. Eğer salt `pytest` komutunda import hatası alıyorsanız kapsam ve ortam farkı mevcuttur.\n"
        )
    
    plan_content = f"# Repair Agent Plan\n\n"
    if is_live_pass:
        plan_content += "Current live test run is PASS. Previous hata_analizi.md entries are stale and were not used for patching.\n\n"
        
    plan_content += f"{diff_analysis}\n## Failed Tests\n"
    if not classifications:
        plan_content += "- None\n"
    for c in classifications:
        plan_content += f"- {c['test']}\n"
        
    plan_content += "\n## Root Causes\n"
    if not classifications:
        plan_content += "- None\n"
    for c in classifications:
        plan_content += f"- {c['root_cause']}\n"
        
    plan_content += "\n## Proposed Fixes\n"
    if not classifications:
        plan_content += "- None\n"
    for c in classifications:
        if c['category'] == "Import/PYTHONPATH problemi" and c['file_to_modify']:
            plan_content += f"- {c['file_to_modify']} dosyasına sys.path.insert eklenecek.\n"
        else:
            plan_content += f"- {c['test']} için manuel inceleme (Risk: {c['risk']}).\n"
            
    plan_content += "\n## Files To Modify\n"
    if not classifications:
        plan_content += "- None\n"
    for c in classifications:
        if c['file_to_modify']:
            plan_content += f"- {c['file_to_modify']}\n"
            
    plan_content += "\n## Risk Level\n"
    highest_risk = "LOW"
    for c in classifications:
        if c['risk'] == "HIGH": highest_risk = "HIGH"
        elif c['risk'] == "MEDIUM" and highest_risk == "LOW": highest_risk = "MEDIUM"
    
    if not classifications:
        highest_risk = "NONE"
        
    plan_content += f"{highest_risk}\n"
    
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan_content)
    
    return plan_path, highest_risk

def is_allowed_to_modify(filepath):
    """Dosyanın değiştirilmesine izin verilip verilmediğini kontrol eder."""
    if not filepath: return False
    
    try:
        # Resolve the absolute path of the file and the current working directory
        abs_filepath = os.path.abspath(filepath)
        abs_cwd = os.path.abspath(os.getcwd())

        # Ensure the file is within the current working directory to prevent path traversal
        if not abs_filepath.startswith(abs_cwd + os.sep):
            return False

        # Get the relative path for directory/file checks
        rel_filepath = os.path.relpath(abs_filepath, abs_cwd).replace("\\", "/")
    except ValueError:
        return False
    
    for forbidden in FORBIDDEN_DIRS:
        if forbidden in rel_filepath.split('/'):
            return False
            
    for forbidden_file in FORBIDDEN_FILES:
        if rel_filepath.endswith(forbidden_file):
            return False
            
    for allowed in ALLOWED_DIRS:
        if rel_filepath.startswith(allowed):
            return True
            
    return False

def apply_safe_fixes(classifications):
    """Sadece LOW veya MEDIUM riskli güvenli düzeltmeleri uygular."""
    applied_fixes = []
    files_modified = set()
    
    for c in classifications:
        if c['risk'] in ["LOW", "MEDIUM"]:
            filepath = c['file_to_modify']
            if filepath and is_allowed_to_modify(filepath) and os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                new_content = content
                
                if c['category'] == "Import/PYTHONPATH problemi":
                    if "import sys" not in content and "sys.path.insert" not in content:
                        patch = (
                            "import os\n"
                            "import sys\n"
                            "sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))\n"
                        )
                        new_content = patch + content
                        applied_fixes.append(f"{filepath} dosyasına import yaması uygulandı.")
                        
                if new_content != content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    files_modified.add(filepath)
            else:
                applied_fixes.append(f"Atlandı (Güvenlik Sınırı): {filepath}")
        else:
            applied_fixes.append(f"Atlandı (Risk HIGH): {c['test']}")
            
    return applied_fixes, list(files_modified)

def write_results(test_agent_out, pytest_out):
    """Sonuçları dosyaya yazar."""
    os.makedirs("output/filestructure", exist_ok=True)
    res_path = "output/filestructure/33_repair_agent_results.txt"
    with open(res_path, "w", encoding="utf-8") as f:
        f.write("=== python test_agent.py --once ===\n")
        f.write(test_agent_out)
        f.write("\n=== python -m pytest ===\n")
        f.write(pytest_out)
    return res_path

def write_go_no_go(initial_failed_count, applied_fixes, files_modified, test_agent_rc, pytest_rc, live_source, historical_status):
    """Nihai durumu rapora döker."""
    os.makedirs("output/filestructure", exist_ok=True)
    report_path = "output/filestructure/34_repair_agent_go_no_go.txt"
    
    decision = "GO" if test_agent_rc == 0 and pytest_rc == 0 else "NO-GO"
    
    fixes_str = "\n".join([f"- {f}" for f in applied_fixes]) if applied_fixes else "- Yok"
    files_str = "\n".join([f"- {f}" for f in files_modified]) if files_modified else "- Yok"
    
    content = f"""REPAIR AGENT GO/NO-GO

Live test source: {live_source}
Historical report status: {historical_status}

Initial result:
- Failed: {initial_failed_count}

Fixes applied:
{fixes_str}

Files modified:
{files_str}

Final validation:
- python test_agent.py --once: {"PASS" if test_agent_rc == 0 else "FAIL"}
- python -m pytest: {"PASS" if pytest_rc == 0 else "FAIL"}

Risk notes:
- Otomatik düzeltmeler sadece LOW ve MEDIUM seviyelerde uygulandı.

Decision:
{decision}
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return decision, report_path

def main():
    parser = argparse.ArgumentParser(description="Repair Agent")
    parser.add_argument("--once", action="store_true", default=True, help="Bir kez çalıştır ve çık.")
    args = parser.parse_args()

    print(">>> Repair Agent başlatılıyor...")
    
    # A. Ön analiz
    report = read_failure_report()
    rc1, out1 = run_test_agent()
    
    # B. Sınıflandırma
    live_failed_tests, historical_failed_tests = parse_failed_tests(out1)
    
    is_live_pass = (rc1 == 0 and len(live_failed_tests) == 0)
    historical_status = "STALE" if is_live_pass and len(historical_failed_tests) > 0 else "FRESH"
    if len(historical_failed_tests) == 0:
        historical_status = "FRESH (None found)"
        
    failed_tests = live_failed_tests if not is_live_pass else []
    initial_failed_count = len(failed_tests)
    
    # Ek analiz için düz pytest koşturalım
    rc_py_initial, out_py_initial = run_pytest()
    
    if is_live_pass:
        print("Canlı testler PASS döndü. Ortam temiz.")
        plan_path, highest_risk = create_repair_plan([], out_py_initial, out1, True)
        write_results(out1, out_py_initial)
        write_go_no_go(0, [], [], rc1, rc_py_initial, "test_agent.py --once", historical_status)
        print(f"\n>>> Final Karar: GO")
        print(f">>> Detaylar: output/filestructure/34_repair_agent_go_no_go.txt")
        return
        
    classifications = classify_failures(failed_tests, out1 + "\n" + report)
    
    # C. Onarım planı
    plan_path, highest_risk = create_repair_plan(classifications, out_py_initial, out1, False)
    print(f">>> Plan oluşturuldu: {plan_path} (Risk: {highest_risk})")
    
    # D. Kod düzeltmesi
    applied_fixes, files_modified = apply_safe_fixes(classifications)
    if applied_fixes:
        print(">>> Uygulanan Düzeltmeler:")
        for f in applied_fixes:
            print(f"    - {f}")
            
    # E. Doğrulama
    rc_test_agent, out_test_agent = run_test_agent()
    rc_pytest, out_pytest = run_pytest()
    
    write_results(out_test_agent, out_pytest)
    
    # F. Go/No-Go
    decision, go_path = write_go_no_go(
        initial_failed_count, 
        applied_fixes, 
        files_modified, 
        rc_test_agent, 
        rc_pytest,
        "test_agent.py --once",
        historical_status
    )
    
    print(f"\n>>> Final Karar: {decision}")
    print(f">>> Detaylar: {go_path}")

if __name__ == "__main__":
    main()
