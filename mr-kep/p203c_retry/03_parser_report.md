# P203C-RETRY — 03 Parser Report

semantic_ok = 19/19 (100%). 0 site/category/section names leaked.

Defects fixed (live-exposed): (1) stale __pycache__; (2) space-less site token -> _is_site_title; (3) dual-h1 masthead -> iterate h1; (4) 'Bottle Name:' prefix stripped; (5) singular -review wrongly excluded -> plural -reviews only.

schema_ok = 19/19 (100%). score.normalized number|null; score.scale_max number|null (patched this retry).
