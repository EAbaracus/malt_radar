import subprocess
import sys
import os

def run_command(command, cwd=None, env=None):
    print(f"\n--- Running: {' '.join(command)} ---")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            shell=False,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_dir = os.path.join(base_dir, "frontend")
    
    python_env = os.environ.copy()
    python_env["PYTHONPATH"] = "backend"

    commands = [
        {
            "name": "Backend DB Smoke & Hardening Tests",
            "cmd": [sys.executable, "-m", "pytest", "tests/test_db_read_api_smoke.py", "tests/test_db_read_service_hardening.py", "-v"],
            "cwd": base_dir,
            "env": python_env
        },
        {
            "name": "i18n Duplicate Keys Test",
            "cmd": [sys.executable, "-m", "pytest", "tests/test_i18n_duplicate_keys.py", "-v"],
            "cwd": base_dir,
            "env": python_env
        },
        {
            "name": "Scraper Contract Test",
            "cmd": [sys.executable, "-m", "pytest", "tests/test_distiller_scraper_contract.py", "-v"],
            "cwd": base_dir,
            "env": python_env
        },
        {
            "name": "Flutter Analyze",
            "cmd": ["flutter", "analyze"],
            "cwd": frontend_dir,
            "env": None
        },
        {
            "name": "Flutter Test: db_api_validation_test",
            "cmd": ["flutter", "test", "test/db_api_validation_test.dart"],
            "cwd": frontend_dir,
            "env": None
        },
        {
            "name": "Flutter Test: real_csv_seed_test",
            "cmd": ["flutter", "test", "test/real_csv_seed_test.dart"],
            "cwd": frontend_dir,
            "env": None
        },
        {
            "name": "Flutter Test: db_seed_test",
            "cmd": ["flutter", "test", "test/db_seed_test.dart"],
            "cwd": frontend_dir,
            "env": None
        },
        {
            "name": "Flutter Test: similar_flavor_test",
            "cmd": ["flutter", "test", "test/similar_flavor_test.dart"],
            "cwd": frontend_dir,
            "env": None
        }
    ]

    pass_count = 0
    fail_count = 0
    failed_commands = []

    for task in commands:
        cmd = task["cmd"]
        # Use shell=True for flutter commands on windows if it's flutter.bat, but subprocess handles flutter.bat if we don't supply shell=True on latest python.
        # But to be safe on Windows, let's resolve 'flutter' to 'flutter.bat' if needed, or just let OS handle it. 
        # Actually shell=True is safer for flutter on Windows if we don't supply full path to flutter.bat
        if cmd[0] == "flutter" and os.name == "nt":
            cmd[0] = "flutter.bat"

        success = run_command(cmd, cwd=task["cwd"], env=task["env"])
        if success:
            pass_count += 1
            print(f"[PASS] {task['name']}")
        else:
            fail_count += 1
            failed_commands.append(task["name"])
            print(f"[FAIL] {task['name']}")

    print("\n======================================")
    print("        RELEASE GATE SUMMARY          ")
    print("======================================")
    print(f"Total PASS : {pass_count}")
    print(f"Total FAIL : {fail_count}")

    if failed_commands:
        print("\nFailed Steps:")
        for fc in failed_commands:
            print(f" - {fc}")
        print("\nFINAL DECISION: NO-GO")
        sys.exit(1)
    else:
        print("\nFINAL DECISION: GO")
        sys.exit(0)

if __name__ == "__main__":
    main()
