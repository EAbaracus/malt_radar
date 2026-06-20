# 203 ScotchGit Manual QA Decision Gate

## Inputs
- QA pack: `C:/Users/eltun/Documents/malt radar/output/reports/201_scotchgit_flavor_manual_qa_pack.csv`
- QA pack SHA256: `bd328f4a91ce3d7d711470739777a7c76935c59f26a79c5dc5f3693898e7ad4b`
- Preview CSV: `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_flavor_signal_preview.csv`
- Preview CSV SHA256: `66e76ece9b55f2d761198600434a46f00be0b0d648350051ad66b32ea1fa469c`

## Output files
- Accepts: `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_flavor_preview_manual_accepts.csv`
- Rejects: `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_flavor_preview_manual_rejects.csv`
- Needs raw note: `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_flavor_preview_needs_raw_note.csv`
- Needs manual match: `C:/Users/eltun/Documents/malt radar/data/output/scotchgit_flavor_preview_needs_manual_match.csv`

## Summary
- QA rows: `255`
- Preview rows: `986`
- accept_preview: `123`
- reject: `80`
- needs_raw_note: `51`
- needs_manual_match: `1`
- pending/empty: `0`

## Decision counts
```text
manual_decision_normalized
accept_preview        123
reject                 80
needs_raw_note         51
needs_manual_match      1
```

## QA group counts
```text
qa_group
islay_smoky_expected                 30
sherry_expected                      30
sweet_fruity_expected                30
zero_signal_review                   30
high_signal_review                   30
random_sample                        30
region_only_low_confidence_review    30
keyword_plus_region_review           27
maritime_expected                    18
```

## Accepted group counts
```text
qa_group
sherry_expected                      28
islay_smoky_expected                 26
high_signal_review                   25
keyword_plus_region_review           16
sweet_fruity_expected                10
maritime_expected                     9
region_only_low_confidence_review     5
random_sample                         4
```

## Accept risk checks
- accept_preview zero signal rows: `0`
- accept_preview region_only rows: `39`
- accept_preview region_only ratio: `31.71%`
- accept_preview rows with confidence_warning: `123`

## Gate decision
- Preview whitelist gate: **GO**
- Production import gate: **NO-GO**

## GO notes
- Manual QA preview whitelist passed.
- This does not authorize production DB import.
- Accepted rows remain preview-only candidates.

## Safety
- `production.db` was not opened or modified by this script.
- Raw Reddit content was not fetched.
- Frontend integration was not performed.
- ScotchGit preview remains `candidate_preview_only`.
