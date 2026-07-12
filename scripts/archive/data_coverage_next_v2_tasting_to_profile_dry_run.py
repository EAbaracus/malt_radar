import os
import csv
import json
import sqlite3
import hashlib
import re
from collections import Counter, defaultdict

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
REPORTS_DIR = "output/reports"

ALL_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v2_profile_candidates.csv")
HIGH_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v2_high_candidates.csv")
REVIEW_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v2_review_candidates.csv")
BLOCKED_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v2_blocked_candidates.csv")

REPORT_MD = os.path.join(REPORTS_DIR, "data_coverage_next_v2_report.md")
GATE_TXT = os.path.join(REPORTS_DIR, "data_coverage_next_v2_gate.txt")

# Lexicon defining terms for each flavor axis
LEXICON = {
    "smoky": ["smoke", "smoky", "bonfire", "ash", "ashes", "charred", "embers", "phenolic", "soot"],
    "peaty": ["peat", "peaty", "peated", "medicinal", "iodine", "tar", "tarry", "phenol", "seaweed", "mossy"],
    "sweet": ["sweet", "sweetness", "honey", "vanilla", "caramel", "toffee", "sugar", "syrup", "butterscotch", "fudge", "molasses", "custard", "maple"],
    "fruity": ["fruit", "fruity", "apple", "pear", "citrus", "orange", "lemon", "lime", "grapefruit", "peach", "apricot", "cherry", "cherries", "berry", "berries", "plum", "plums", "raisin", "raisins", "sultana", "sultanas", "fig", "figs", "banana", "pineapple", "melon", "coconut"],
    "spicy": ["spice", "spicy", "pepper", "peppery", "cinnamon", "nutmeg", "ginger", "clove", "cloves", "cardamom", "aniseed", "licorice", "chili"],
    "woody": ["oak", "wood", "woody", "cask", "barrel", "tannic", "tannins", "sawdust", "cedar", "pine", "resin", "leather", "tobacco"],
    "floral": ["floral", "flower", "flowers", "heather", "perfume", "perfumed", "lavender", "rose", "violet", "violets", "elderflower", "jasmine", "blossom"]
}

AXES = ["smoky", "peaty", "sweet", "fruity", "spicy", "woody", "floral"]

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def main():
    print("=== Running DATA-COVERAGE-NEXT-V2 Tasting Notes to Profile Dry-Run ===")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    hash_before = get_file_hash(DB_PATH)
    
    # Connect to DB in read-only mode
    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 1. Fetch whiskies that have tasting notes but no flavor profile (P1 Candidates)
    p1_whiskies = cur.execute("""
        SELECT w.whisky_id, w.name, w.distillery_id
        FROM whiskies w
        WHERE w.whisky_id IN (SELECT DISTINCT whisky_id FROM tasting_notes)
          AND w.whisky_id NOT IN (SELECT DISTINCT whisky_id FROM flavor_profiles)
    """).fetchall()
    
    candidates = []
    
    fk_missing_count = 0
    duplicate_candidate_count = 0
    invalid_score_count = 0
    already_exists_count = 0
    
    seen_ids = set()
    source_system_counts = Counter()
    all_evidence_terms = []
    
    for w in p1_whiskies:
        wid = w["whisky_id"]
        
        # Check duplicate candidates
        if wid in seen_ids:
            duplicate_candidate_count += 1
            continue
        seen_ids.add(wid)
        
        # Verify FK presence in whiskies table
        whisky_check = cur.execute("SELECT COUNT(*) FROM whiskies WHERE whisky_id = ?", (wid,)).fetchone()[0]
        if whisky_check == 0:
            fk_missing_count += 1
            classification = "BLOCKED"
            candidates.append({
                "whisky_id": wid, "name": w["name"], "distillery_id": w["distillery_id"] or "",
                "smoky": 0.0, "peaty": 0.0, "sweet": 0.0, "fruity": 0.0, "spicy": 0.0, "woody": 0.0, "floral": 0.0,
                "evidence_terms": "", "note_count": 0, "sources": "Unknown", "classification": classification
            })
            continue
            
        # Verify flavor profile already exists
        profile_check = cur.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id = ?", (wid,)).fetchone()[0]
        if profile_check > 0:
            already_exists_count += 1
            
        # Retrieve tasting notes
        notes = cur.execute("""
            SELECT nose_notes, palate_notes, finish_notes, source_system
            FROM tasting_notes
            WHERE whisky_id = ?
        """, (wid,)).fetchall()
        
        note_count = len(notes)
        sources = [n["source_system"] for n in notes if n["source_system"] is not None]
        for s in sources:
            source_system_counts[s] += 1
        sources_str = ", ".join(set(sources)) if sources else "Unknown"
        
        # Combine texts
        text_parts = []
        for n in notes:
            text_parts.append(str(n["nose_notes"] or ""))
            text_parts.append(str(n["palate_notes"] or ""))
            text_parts.append(str(n["finish_notes"] or ""))
        combined_text = " ".join(text_parts).lower()
        
        # Lexicon scoring
        raw_scores = {axis: 0 for axis in AXES}
        matched_words = []
        
        for axis, keywords in LEXICON.items():
            for word in keywords:
                escaped = re.escape(word)
                matches = re.findall(rf"\b{escaped}(?:ed|y|s)?\b", combined_text)
                if matches:
                    raw_scores[axis] += len(matches)
                    matched_words.append(word)
                    
        # Unique evidence terms
        evidence_terms_list = sorted(list(set(matched_words)))
        all_evidence_terms.extend(evidence_terms_list)
        evidence_terms_str = ", ".join(evidence_terms_list[:12])
        
        # Normalize
        max_raw = max(raw_scores.values()) if raw_scores else 0
        scores = {}
        for axis in AXES:
            val = raw_scores[axis]
            if max_raw > 0:
                norm_score = round(val / max_raw, 4)
            else:
                norm_score = 0.0
            scores[axis] = norm_score
            
            # Score validity check
            if norm_score < 0.0 or norm_score > 1.0:
                invalid_score_count += 1

        # Classify candidate
        active_dimensions = sum(1 for axis in AXES if scores[axis] > 0)
        evidence_count = len(evidence_terms_list)
        
        if not combined_text.strip() or max_raw == 0 or evidence_count == 0:
            classification = "BLOCKED"
        elif active_dimensions >= 3 and max(scores.values()) >= 0.45 and evidence_count >= 4 and note_count >= 1:
            classification = "HIGH"
        else:
            classification = "REVIEW"
            
        candidates.append({
            "whisky_id": wid,
            "name": w["name"],
            "distillery_id": w["distillery_id"] or "",
            "smoky": scores["smoky"],
            "peaty": scores["peaty"],
            "sweet": scores["sweet"],
            "fruity": scores["fruity"],
            "spicy": scores["spicy"],
            "woody": scores["woody"],
            "floral": scores["floral"],
            "evidence_terms": evidence_terms_str,
            "note_count": note_count,
            "sources": sources_str,
            "classification": classification
        })
        
    conn.close()
    
    # 2. Write CSV outputs
    high_candidates = [c for c in candidates if c["classification"] == "HIGH"]
    review_candidates = [c for c in candidates if c["classification"] == "REVIEW"]
    blocked_candidates = [c for c in candidates if c["classification"] == "BLOCKED"]
    
    fieldnames = ["whisky_id", "name", "distillery_id", "smoky", "peaty", "sweet", "fruity", "spicy", "woody", "floral", "evidence_terms", "note_count", "sources", "classification"]
    
    def write_csv(path, rows):
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
    write_csv(ALL_CSV, candidates)
    write_csv(HIGH_CSV, high_candidates)
    write_csv(REVIEW_CSV, review_candidates)
    write_csv(BLOCKED_CSV, blocked_candidates)
    
    # Check DB Hash stability
    hash_after = get_file_hash(DB_PATH)
    hash_same = (hash_before == hash_after)
    
    # Verdict decision
    verdict = "GO"
    if not hash_same or len(candidates) != 62 or invalid_score_count > 0 or duplicate_candidate_count > 0:
        verdict = "NO-GO"
        
    # Write Gate status
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write(verdict)
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        
    # Top evidence terms
    top_evidence = Counter(all_evidence_terms).most_common(10)
    top_evidence_str = ", ".join([f"{word} ({cnt})" for word, cnt in top_evidence])
    
    # Generate report markdown
    report = []
    report.append("# DATA-COVERAGE-NEXT-V2 — Tasting Notes to Flavor Profile Dry-Run Report\n")
    report.append(f"- **Verdict:** **{verdict}**")
    report.append(f"- **P1 Candidates Processed:** `{len(candidates)}`")
    report.append(f"- **HIGH Candidates:** `{len(high_candidates)}`")
    report.append(f"- **REVIEW Candidates:** `{len(review_candidates)}`")
    report.append(f"- **BLOCKED Candidates:** `{len(blocked_candidates)}`\n")
    
    report.append("## Verification checklist")
    report.append(f"- Database Hash Matches: {'✅ Yes' if hash_same else '❌ NO! DANGER'}")
    report.append(f"- Expected Candidates Count (62): {'✅ Yes' if len(candidates) == 62 else f'❌ Got {len(candidates)}'}")
    report.append(f"- FK missing count: {fk_missing_count}")
    report.append(f"- Duplicate whisky_id count: {duplicate_candidate_count}")
    report.append(f"- Invalid score range count: {invalid_score_count}")
    report.append(f"- Already exists profile conflict count: {already_exists_count}\n")
    
    report.append("## Source System Distribution")
    for s, cnt in source_system_counts.items():
        report.append(f"- {s}: {cnt} notes")
    report.append("")
    
    report.append("## Top Matching Evidence Terms")
    report.append(f"- {top_evidence_str}\n")
    
    report.append("## Top 20 HIGH Candidates Examples")
    report.append("| Whisky ID | Name | Distillery ID | Scores (Sm, Pe, Sw, Fr, Sp, Wo, Fl) | Evidence Terms | Notes Count |")
    report.append("| --- | --- | --- | --- | --- | --- |")
    for c in high_candidates[:20]:
        scores_str = f"({c['smoky']:.2f}, {c['peaty']:.2f}, {c['sweet']:.2f}, {c['fruity']:.2f}, {c['spicy']:.2f}, {c['woody']:.2f}, {c['floral']:.2f})"
        report.append(f"| {c['whisky_id']} | {c['name']} | {c['distillery_id']} | {scores_str} | {c['evidence_terms']} | {c['note_count']} |")
    report.append("")

    report.append("## Recommended Next Phase")
    report.append("**DATA-COVERAGE-NEXT-V3 — Manual QA Pack**")
    report.append("Export candidate csv files for review and staging simulation preparation.")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    print("Dry-run completed successfully.")

if __name__ == "__main__":
    main()
