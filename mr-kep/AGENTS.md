# MR-KEP — Agent Operating Instructions

MR-KEP is governed by the same principles as the broader Malt Radar AOS
(read-only first, evidence-first, deterministic, no fabrication). This file
defines the **agent roles** that operate the MR-KEP pipeline and their
boundaries. AOUS consumes this file to assign work to agents.

## Default mode

Start **read-only**. Inspect standards (`authority/`, `schemas/`, `templates/`)
before acting. Never assume a write is required.

## Agent roles

### 1. Qualification Agent
- **Stage:** qualification
- **Input:** source units (per `source_profile.yaml` scope)
- **Output:** qualification record (schema: `schemas/qualification.schema.json`)
- **Responsibility:** Deterministically decide which source units are
  `in_scope` / `out_of_scope` / `deferred`. **No content extraction.**
- **Rules:** Apply only the declared `qualification` rules. Record a reason per
  unit. Never modify production.

### 2. Extraction Agent
- **Stage:** extraction
- **Input:** qualified units
- **Output:** extraction record (schema: `schemas/extraction.schema.json`)
- **Responsibility:** Pull raw field values WITH a verbatim `quote` from the
  source text, using only declared `extraction_methods`. No normalization, no
  judgment, no merging.
- **Rules:** Every field value must carry a `quote`. If the source does not
  state a field, emit `null` — never invent.

### 3. Validation Agent
- **Stage:** validation
- **Input:** extraction records
- **Output:** normalized + validated records
- **Responsibility:** Apply `field_rules.yaml` normalization keys; verify
  evidence_type matches; compute preliminary confidence; reject fields that
  violate `authority_ceiling`.
- **Rules:** A field extracted by a too-low authority tier for its category is
  REJECTED (not silently kept). Normalization failures lower confidence.

### 4. Merge Agent
- **Stage:** merge
- **Input:** validated records for the same whisky (matched via IoU threshold)
- **Output:** merged record per `merge_policies.yaml`
- **Responsibility:** Resolve conflicts deterministically using authority tier,
  source priority, and the named merge policy. Keep losing candidates as
  evidence. Route unresolvable conflicts to Audit.
- **Rules:** Apply `reject_on_conflict` for identity fields. Never drop a
  loser's provenance.

### 5. Certification Agent
- **Stage:** certification
- **Input:** merged records
- **Output:** certification record (schema: `schemas/certification.schema.json`)
- **Responsibility:** Attach an evidence record to every certified field;
  enforce `certify_min_confidence` (0.70). Mark `audit_status = pending_audit`.
- **Rules:** Does NOT write production. Promotion only on a later explicit
  apply gate (read-only verification).

### 6. Audit Agent
- **Stage:** audit
- **Input:** certification records + any routed conflicts
- **Output:** audit report + final gate
- **Responsibility:** Verify every certified fact has valid evidence; flag
  facts below `audit_warn_below` (0.60); evaluate the run gate
  (GO / PARTIAL_GO / NO_GO / AWAITING_APPROVAL).
- **Rules:** Read-only. May recommend rejection but performs no production write.

## Completion requirements (every agent)

Before reporting success an agent must: verify outputs against the relevant
JSON Schema, verify internal consistency, and record provenance. No agent may
write to `production.db`.

## Escalation

When confidence is low or a conflict cannot be resolved deterministically:
**stop, explain, route to Audit Agent.** Never guess.

---

## Web Search & Extraction

Three-tier web stack. All sub-agents have the same tools — use them deliberately.

| Tier | Tool | Address | Role |
|------|------|---------|------|
| 1 | SearXNG | `localhost:8090` | Primary search backend. Aggregates Google, DDG, Startpage. Server-side engine filtering. Search-only — no URL extraction. Config: `searxng/settings.yml` (under `search-stack/`). |
| 1 | Firecrawl | `http://localhost:3002` | Primary extraction backend. Handles standard sites, PDFs, structured extraction. |
| 2 | Hound MCP | local MCP server | Anti-bot fallback for sites that block Firecrawl. Registers four tools: `smart_fetch`, `smart_search`, `smart_crawl`, `screenshot`. |

### Escalation path

- **SearXNG + Firecrawl** — always try first. Fast, token-efficient.
- **Hound `smart_fetch`** — when Firecrawl hits 403/CAPTCHA/empty. Handles Cloudflare Turnstile, DataDome.
- **Hound `smart_crawl`** — for deep crawling behind bot protection.
- **Hound `smart_search`** — fallback search if SearXNG is down.
