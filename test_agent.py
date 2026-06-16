import os
import sys
import json
import time
import hashlib
import asyncio
import argparse
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Antigravity SDK Simulation ---
# Standart Python ortamında 'antigravity' modülü xkcd easter egg'i olduğundan
# ve isim çakışması yarattığından, bu script test süreçlerini doğrudan
# yerleşik (built-in) subprocess modülüyle, otonom bir ajan gibi davranarak yürütür.
# Ana proje dosyalarını değiştirmez (read-only), sadece rapor üretir.
# ----------------------------------

# Konsol çıktılarında UTF-8 garantisi
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Konfigürasyon
STATE_FILE = ".test_agent_state.json"
REPORT_FILE = "hata_analizi.md"
WATCH_EXTENSIONS = {'.py', '.dart', '.yaml', '.yml', '.json'}
IGNORE_DIRS = {'.git', '.venv', 'venv', 'node_modules', '.dart_tool', 'build', 'dist', '__pycache__', 'output'}
IGNORE_FILES = {STATE_FILE, REPORT_FILE}
DEFAULT_COMMAND = "python -m pytest"
DEFAULT_TIMEOUT = 300
DEBOUNCE_SECONDS = 2

class AgentState:
    def __init__(self, workspace_path):
        self.state_file_path = os.path.join(workspace_path, STATE_FILE)
        self.fingerprints = []

    def load_state(self):
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.fingerprints = data.get("fingerprints", [])
            except Exception:
                self.fingerprints = []

    def save_state(self):
        try:
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                json.dump({"fingerprints": self.fingerprints}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Uyarı: State dosyası kaydedilemedi: {e}")

    def add_fingerprint(self, fingerprint):
        if fingerprint not in self.fingerprints:
            self.fingerprints.append(fingerprint)
            self.save_state()
            return True
        return False

def should_ignore_path(path_str):
    p = Path(path_str)
    
    if p.suffix not in WATCH_EXTENSIONS:
        return True
    
    parts = p.parts
    for ignored in IGNORE_DIRS:
        if ignored in parts:
            return True
            
    if "output/test_agent" in str(p).replace("\\", "/"):
        return True
    
    if p.name in IGNORE_FILES:
        return True
    
    return False

def analyze_failure(output_text):
    broken_tests = []
    root_causes = []
    
    lines = output_text.splitlines()
    for line in lines:
        if "FAILED " in line or "ERROR " in line:
            broken_tests.append(line.strip())
        elif "Error:" in line or "Exception:" in line:
            root_causes.append(line.strip())
            
    if not broken_tests:
        broken_tests = ["Belirgin bir FAILED satırı bulunamadı, ancak exit code 0 değil."]
    if not root_causes:
        root_causes = ["Loglarda doğrudan belirgin bir Exception veya Error işareti bulunamadı."]
        
    return broken_tests, root_causes

def write_failure_report(workspace_path, command, exit_code, broken_tests, root_causes, raw_output):
    report_path = os.path.join(workspace_path, REPORT_FILE)
    
    lines = raw_output.splitlines()
    if len(lines) > 50:
        summary_log = "\n".join(lines[:20] + ["...", f"({len(lines)-40} satır gizlendi)", "..."] + lines[-20:])
    else:
        summary_log = raw_output

    broken_str = "\n".join([f"* {t}" for t in broken_tests])
    cause_str = "\n".join([f"* {c}" for c in root_causes])

    report_content = f"""# Test Hata Analizi

## Özet
Testler `{exit_code}` çıkış kodu ile başarısız oldu. Lütfen logları inceleyin.

## Çalıştırılan Komut
```bash
{command}
```

## Exit Code
{exit_code}

## Kırılan Testler
{broken_str}

## Muhtemel Kök Nedenler
{cause_str}

## Çözüm Önerileri
* Kırılan testlerle ilgili kod bloklarını gözden geçirin.
* Hata loglarındaki çağrı yığınını (stack trace) takip edin.

## Ham Log Özeti
```text
{summary_log}
```
"""
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
    except Exception as e:
        print(f"Uyarı: Rapor dosyası ({REPORT_FILE}) yazılamadı: {e}")

def create_github_issue_if_needed(workspace_path, state, broken_tests):
    auto_issue = os.environ.get("AUTO_GITHUB_ISSUE", "false").lower() == "true"
    if not auto_issue:
        return

    content_to_hash = "".join(broken_tests).encode('utf-8')
    fingerprint = hashlib.md5(content_to_hash).hexdigest()

    if not state.add_fingerprint(fingerprint):
        print("Uyarı: Aynı hata daha önce raporlandığı için yeni issue açılmıyor.")
        return

    report_path = os.path.join(workspace_path, REPORT_FILE)
    issue_title = f"Test Hatası: {fingerprint[:8]}"
    
    try:
        issue_cmd = f'gh issue create --title "{issue_title}" --body-file "{report_path}"'
        res = subprocess.run(issue_cmd, shell=True, capture_output=True, text=True, cwd=workspace_path)
        if res.returncode == 0:
            print(f"GitHub Issue açıldı: {issue_title}")
        else:
            print("Uyarı: GitHub Issue açılamadı. 'gh' komutu kurulu mu veya oturum açık mı?")
    except Exception as e:
        print(f"Uyarı: Issue oluşturulurken hata: {e}")

async def run_tests(workspace_path, state):
    command = os.environ.get("TEST_AGENT_COMMAND", DEFAULT_COMMAND)
    timeout = int(os.environ.get("TEST_AGENT_TIMEOUT", DEFAULT_TIMEOUT))
    
    env = os.environ.copy()
    project_root = Path(workspace_path).resolve()
    backend_path = project_root / "backend"

    existing_pythonpath = env.get("PYTHONPATH", "")
    pythonpath_parts = [
        str(project_root),
        str(backend_path),
    ]

    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)

    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace_path,
            env=env
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            stdout, stderr = await process.communicate()
            output = stdout.decode('utf-8', errors='ignore') + stderr.decode('utf-8', errors='ignore')
            output += f"\n\nHATA: Test komutu {timeout} saniye içinde tamamlanamadığı için iptal edildi (Timeout)."
            return_code = -1
        else:
            output = stdout.decode('utf-8', errors='ignore') + stderr.decode('utf-8', errors='ignore')
            return_code = process.returncode
            
        if return_code == 0:
            print("Başarılı")
        else:
            broken_tests, root_causes = analyze_failure(output)
            write_failure_report(workspace_path, command, return_code, broken_tests, root_causes, output)
            create_github_issue_if_needed(workspace_path, state, broken_tests)
            print("Hata raporu oluşturuldu.")
            
    except Exception as e:
        print(f"Test komutu çalıştırılamadı: {e}")

class AgentRunner:
    def __init__(self, workspace_path):
        self.workspace_path = workspace_path
        self.state = AgentState(workspace_path)
        self.state.load_state()
        self.is_running = False
        self.pending_run = False
        
    async def trigger_run(self):
        if self.is_running:
            self.pending_run = True
            return
            
        self.is_running = True
        self.pending_run = False
        
        try:
            await run_tests(self.workspace_path, self.state)
        finally:
            self.is_running = False
            if self.pending_run:
                # Bekleyen testi çalıştır
                asyncio.create_task(self.trigger_run())

class SourceChangeHandler(FileSystemEventHandler):
    def __init__(self, runner, loop):
        self.runner = runner
        self.loop = loop
        self.last_trigger = 0

    def on_modified(self, event):
        if event.is_directory or should_ignore_path(event.src_path):
            return
            
        current_time = time.time()
        if current_time - self.last_trigger > DEBOUNCE_SECONDS:
            self.last_trigger = current_time
            asyncio.run_coroutine_threadsafe(self.runner.trigger_run(), self.loop)

async def watch_mode(workspace_path):
    runner = AgentRunner(workspace_path)
    await runner.trigger_run()
    
    loop = asyncio.get_running_loop()
    event_handler = SourceChangeHandler(runner, loop)
    observer = Observer()
    observer.schedule(event_handler, path=workspace_path, recursive=True)
    observer.start()
    
    print("Otonom test ajanı (izleme modu) başlatıldı. Kaynak kod değişiklikleri bekleniyor...")
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        observer.stop()
        print("İzleme sonlandırılıyor...")
    observer.join()

async def once_mode(workspace_path):
    runner = AgentRunner(workspace_path)
    await runner.trigger_run()

def main():
    parser = argparse.ArgumentParser(description="Otonom Test Ajanı")
    parser.add_argument("--once", action="store_true", help="Testleri bir kez çalıştırır ve çıkar.")
    parser.add_argument("--watch", action="store_true", help="Dosya değişikliklerini izler ve otomatik test çalıştırır.")
    args = parser.parse_args()
    
    workspace_path = os.path.abspath(os.path.dirname(__file__))
    
    try:
        if args.once:
            asyncio.run(once_mode(workspace_path))
        else:
            asyncio.run(watch_mode(workspace_path))
    except KeyboardInterrupt:
        print("\nTest ajanı durduruldu.")

if __name__ == "__main__":
    main()
