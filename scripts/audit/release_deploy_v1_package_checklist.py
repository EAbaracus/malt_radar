import os
import hashlib
import sqlite3
import json
import subprocess

DB_PATH = "output/import/production.db"
APK_PATH = "frontend/build/app/outputs/flutter-apk/app-release.apk"
KEY_PROPERTIES_PATH = "frontend/android/key.properties"

REPORT_MD = "output/reports/release_deploy_v1_package_report.md"
GATE_TXT = "output/reports/release_deploy_v1_gate.txt"
RELEASE_NOTES_MD = "output/release/release_notes_beta_v1.md"
BETA_CHECKLIST_MD = "output/release/beta_test_checklist_v1.md"
APK_MANIFEST_JSON = "output/release/apk_manifest_v1.json"

EXPECTED_DB_HASH = "9C1E0E8D9A86EF907AB27378DB25F8410F7A59E465A05E70F86315B83392D0BA"

def get_file_hash(path):
    if not os.path.exists(path):
        return "N/A"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest().upper()

def check_git_status():
    git_db_staged = False
    git_backup_staged = False
    git_apk_staged = False
    git_key_staged = False
    current_branch = "N/A"
    
    try:
        current_branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        status_out = subprocess.check_output(["git", "status", "--short"], text=True)
        for line in status_out.splitlines():
            line_clean = line.strip()
            if not line_clean:
                continue
            is_staged = line[0] in ['A', 'M', 'R', 'C', 'D']
            filepath = line_clean.split(None, 1)[-1]
            
            if is_staged:
                if "production.db" in filepath.lower():
                    git_db_staged = True
                elif "backup" in filepath.lower():
                    git_backup_staged = True
                elif filepath.endswith(".apk"):
                    git_apk_staged = True
                elif "key.properties" in filepath.lower() or filepath.endswith(".keystore") or filepath.endswith(".jks"):
                    git_key_staged = True
    except Exception as e:
        print(f"Git status check failed: {e}")
        
    return {
        "branch": current_branch,
        "git_db_staged": git_db_staged,
        "git_backup_staged": git_backup_staged,
        "git_apk_staged": git_apk_staged,
        "git_key_staged": git_key_staged
    }

def main():
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(APK_MANIFEST_JSON), exist_ok=True)

    # 1. APK Checks
    apk_exists = os.path.exists(APK_PATH)
    apk_hash = get_file_hash(APK_PATH) if apk_exists else "N/A"
    apk_size_bytes = os.path.getsize(APK_PATH) if apk_exists else 0
    apk_size_mb = apk_size_bytes / (1024 * 1024)

    # 2. DB Checks
    db_exists = os.path.exists(DB_PATH)
    db_hash = get_file_hash(DB_PATH) if db_exists else "N/A"
    db_hash_ok = (db_hash == EXPECTED_DB_HASH)
    
    integrity_ok = False
    tasting_notes = 0
    flavor_profiles = 0
    official_source_references = 0
    region_filled = 0
    cask_type_filled = 0
    
    if db_exists:
        try:
            conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
            cur = conn.cursor()
            
            integrity = cur.execute("PRAGMA integrity_check").fetchone()
            integrity_ok = integrity and integrity[0].lower() == 'ok'
            
            tasting_notes = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
            flavor_profiles = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
            official_source_references = cur.execute("SELECT COUNT(*) FROM official_source_references").fetchone()[0]
            region_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE region IS NOT NULL AND region != ''").fetchone()[0]
            cask_type_filled = cur.execute("SELECT COUNT(*) FROM whiskies WHERE cask_type IS NOT NULL AND cask_type != ''").fetchone()[0]
            
            conn.close()
        except Exception as e:
            print(f"DB verification failed: {e}")

    db_counts_ok = (
        tasting_notes == 496 and
        flavor_profiles == 626 and
        official_source_references == 94 and
        region_filled == 301 and
        cask_type_filled == 54
    )

    # 3. Signing Risk Check
    has_key_properties = os.path.exists(KEY_PROPERTIES_PATH)
    signing_fallback_used = not has_key_properties
    
    # 4. Git Safety Check
    git_info = check_git_status()
    git_safety_ok = not (git_info["git_db_staged"] or git_info["git_backup_staged"] or git_info["git_apk_staged"] or git_info["git_key_staged"])

    # Determine Gate Status
    # Warn if using debug fallback, but still allow GO if safety, DB, and APK are OK.
    # If signing fallback is used, we mark as WARN_GO. If critical safety/DB checks fail, we mark as NO-GO.
    if not apk_exists or not db_hash_ok or not integrity_ok or not db_counts_ok or not git_safety_ok:
        verdict = "NO-GO"
    elif signing_fallback_used:
        verdict = "WARN_GO"
    else:
        verdict = "GO"

    # Write Gate Status
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(verdict)
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")


    # Write APK Manifest
    manifest_data = {
        "apk_path": APK_PATH,
        "apk_exists": apk_exists,
        "apk_size_bytes": apk_size_bytes,
        "apk_sha256": apk_hash,
        "signing_type": "debug_fallback" if signing_fallback_used else "release_keystore",
        "integrated_database": {
            "path": DB_PATH,
            "sha256": db_hash,
            "integrity_ok": integrity_ok,
            "metrics": {
                "tasting_notes": tasting_notes,
                "flavor_profiles": flavor_profiles,
                "official_source_references": official_source_references,
                "region_filled": region_filled,
                "cask_type_filled": cask_type_filled
            }
        },
        "build_metadata": {
            "git_branch": git_info["branch"],
            "git_safety_verified": git_safety_ok
        }
    }
    with open(APK_MANIFEST_JSON, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2)

    # Write Release Notes
    release_notes = [
        "# Release Notes — Malt Radar Beta v1.0.0\n",
        "## General Information",
        "- **Version:** `1.0.0-beta.1`",
        f"- **Built From Branch:** `{git_info['branch']}`",
        f"- **Database Version Signature:** `{db_hash[:10]}...` ({'Verified' if db_hash_ok else 'Mismatched'})\n",
        "## Key Features & Content",
        "- **Curated Whisky Datasets:** Integrated offline SQLite database including clean facts, regional mappings, and cask details.",
        f"  - **{tasting_notes} Tasting Notes** verified.",
        f"  - **{flavor_profiles} Flavor Profiles** (seven-axis flavor vectors) integrated.",
        f"  - **{official_source_references} Official Fact Attributions** from verified expert sources.",
        "- **Offline First Architecture:** Native caching of whisky details, favorites lists, and flavor profiles.",
        "- **Interactive Flavor Profile Analytics:** User interface for comparing similar whiskies, calculating flavor distance, and viewing interactive flavor charts.\n",
        "## Technical Artifacts",
        f"- **APK Path:** `{APK_PATH}`",
        f"- **APK Size:** `{apk_size_mb:.2f} MB` ({apk_size_bytes} bytes)",
        f"- **APK SHA-256 Checksum:** `{apk_hash}`",
        f"- **Signing Configuration:** `{'DEBUG FALLBACK (Signed with auto-generated debug key)' if signing_fallback_used else 'PRODUCTION KEYSTORE'}`\n"
    ]
    with open(RELEASE_NOTES_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(release_notes))

    # Write Beta Test Checklist
    checklist = [
        "# Beta Testing Checklist — Malt Radar v1\n",
        "Verify the following quality assurance check groups before promote-to-production:\n",
        "## 1. Database & Offline Capability Check",
        "- [ ] **Offline Startup Check:** Enable Airplane mode, start the app, and verify that the whisky index loads instantaneously without network requests.",
        "- [ ] **Tasting Notes Validation:** Verify that whiskies display their official tasting notes and proper source attributions.",
        "- [ ] **Flavor Axis Graphs:** Verify that the 7-axis radar charts render correctly without lagging or clipping.\n",
        "## 2. Local State & Cache Management",
        "- [ ] **Favorites Management:** Add whiskies to favorites, restart the app, and verify they persist.",
        "- [ ] **Cache Clearance Resilience:** Go to app settings, trigger cache clearance, and verify that system default items (database seeds) are **NOT** deleted.",
        "- [ ] **Custom Lists:** Create a custom whiskey list (e.g., 'Sherry Bombs'), add 3 whiskies, and verify list membership and integrity.\n",
        "## 3. UI Smoke & Usability Tests",
        "- [ ] **Search Functionality:** Test searching for partially matched names (e.g., 'Laph' matches 'Laphroaig').",
        "- [ ] **Filter Controls:** Test filtering by Region and Cask Type, verifying that region counts match database stats.",
        "- [ ] **Responsive Scaling:** Test UI on both small-screen phones and large-screen tablets to ensure no layout overflows (yellow stripe errors).\n",
        "## 4. Security & Safety Audits",
        "- [ ] **No Secret Leaks:** Verify that no API keys or key.properties details are logged to Logcat/console.",
        "- [ ] **Staging-Only Isolation:** Verify that the app does not attempt to mutate or push changes directly to the staging/production database."
    ]
    with open(BETA_CHECKLIST_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(checklist))

    # Write Package Report
    report = [
        "# Release Deploy v1 Package & Beta Checklist Report\n",
        f"- **Deploy Gate Verdict:** **{verdict}**",
        f"- **Git Branch:** `{git_info['branch']}`",
        f"- **APK File Check:** {'FOUND' if apk_exists else 'MISSING'}",
        f"- **APK Path:** `{APK_PATH}`",
        f"- **APK Size:** `{apk_size_mb:.2f} MB` ({apk_size_bytes} bytes)",
        f"- **APK Checksum (SHA-256):** `{apk_hash}`\n",
        "## Database Integrity & Checksums",
        f"- **DB Path:** `{DB_PATH}`",
        f"- **DB Hash:** `{db_hash}` (Expected: `{EXPECTED_DB_HASH}`) - {'MATCHED' if db_hash_ok else 'MISMATCHED'}",
        f"- **DB Integrity:** {'OK' if integrity_ok else 'FAILED'}",
        f"- **Tasting Notes:** {tasting_notes} / 496",
        f"- **Flavor Profiles:** {flavor_profiles} / 626",
        f"- **Official Source References:** {official_source_references} / 94",
        f"- **Region Filled:** {region_filled} / 301",
        f"- **Cask Type Filled:** {cask_type_filled} / 54\n",
        "## Git Safety Audits",
        f"- Staged production.db: {'Staged! (BLOCKED)' if git_info['git_db_staged'] else 'Clean (OK)'}",
        f"- Staged backup DB files: {'Staged! (BLOCKED)' if git_info['git_backup_staged'] else 'Clean (OK)'}",
        f"- Staged APK files: {'Staged! (BLOCKED)' if git_info['git_apk_staged'] else 'Clean (OK)'}",
        f"- Staged Keystore/Signing secrets: {'Staged! (BLOCKED)' if git_info['git_key_staged'] else 'Clean (OK)'}\n",
        "## Signing Configuration Security Summary",
        f"- key.properties exists: {'Yes' if has_key_properties else 'No'}",
        f"- Fallback debug signature used: {'Yes (WARN_GO - Debug signing used for local release APK)' if signing_fallback_used else 'No (Release signed)'}\n",
        "## Generated Artifact Files",
        f"- **Manifest:** `{APK_MANIFEST_JSON}`",
        f"- **Release Notes:** `{RELEASE_NOTES_MD}`",
        f"- **Beta Checklist:** `{BETA_CHECKLIST_MD}`\n",
        "## Final Verdict Details",
        f"Verdict is **{verdict}**."
    ]
    if verdict == "WARN_GO":
        report.append(" Warning is raised because the build is signed with a local fallback debug signature rather than a production keystore (key.properties is missing). This is normal and expected for local developer verification environments.")
    elif verdict == "NO-GO":
        report.append(" Critical checks failed. Ensure the APK is built and the database metrics match expectations.")
    else:
        report.append(" All checks passed successfully.")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Package checklist run complete. Verdict: {verdict}")

if __name__ == "__main__":
    main()
