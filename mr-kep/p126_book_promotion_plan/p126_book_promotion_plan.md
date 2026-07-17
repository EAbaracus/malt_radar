# P126 — Book Knowledge Promotion Plan (READ-ONLY)

**Mode:** READ-ONLY plan. Quantifies per-book DB impact from P125 evidence, measures overlap vs `production.db` (gate), separates already-represented / improved / new, ranks promotion candidates. NO staging/production/evidence write.

## Methodology

- Source: 44 P125 `_evidence/*.jsonl` (read-only) + prior B4b/SMWS extraction evidence.

- Reference entities (production.db, gate-read): distilleries 2144, whiskies 4749, brands 471, bottlers 0.

- New-entity test: each extracted candidate fuzzy-matched (difflib, ratio≥0.85) vs reference lists; unmatched = new; matched = merge candidate.

- Overlap% = known_mentions / (known + new). Separation: ≥0.50 ALREADY_REPRESENTED, 0.25–0.50 IMPROVED_EXISTING, <0.25 COMPLETELY_NEW.

- Impact = 10·new_dist + 3·new_expr + 5·new_brand + 8·new_bott + 0.05·flavor + 0.5·terms + 1·facts + 20 if COMPLETELY_NEW.


## Recommended Promotion Order (optimal)

1. **SMWS USA Archive** (792 cask vectors + 13,238 rows) — exclusive evidence, review-gate promote.

2. **Malt Whisky Yearbook 2019** (B1) — distillery backbone, reliability 5.

3. **B4b Jim Murray Complete Book** — 536 distillery candidates → resolver.

4. **B5 flavor methodology** (Whisky Classified + Flavour of Whisky) — normalize 7-axis vectors.

5. **B2/B3 + Japanese Whisky** — region/history + weakest world subdomain.

6. Resolve new-entity candidates via resolver (low overlap books first).

7. LOW tier (Advocate/annuals/guides) last — high overlap, low net-new.


## GO Verdict
**GO WITH WARNINGS.** All impact is quantified from real extracted evidence; overlap measured against live production.db; no mutation performed. WARNING: 30,529 new-entity candidates require resolver review (do not auto-insert); books #27–29 (Scotch Whisky Annuals) had 0 extractable text → OCR needed before promotion; annas-arch (#42) is a byte-duplicate of #11 → promote once.
