# Rule 08: AOS Cost Policy

This rule governs how the Agent Operating System (AOS) spends money and compute.
It is mandatory for every gate report and every execution decision.

## Default Execution Policy

Every task MUST start in this mode unless explicitly overridden:

- **Local** — run on the local machine / local compute
- **Offline** — do not require network access to complete standard work
- **Deterministic** — same input produces the same output; no hidden randomness

## LLM Usage Is Optional

LLM usage is **OPTIONAL** and must **never be required** for the standard
Malt Radar pipeline.

The pipeline must be able to complete end-to-end using only local deterministic
processing. Any LLM step is an enhancement, not a dependency.

## Priority Order (strict)

When a task needs computation, select the cheapest viable option in this order:

1. **Local deterministic processing** (regex, SQLite, fuzzy match, rules) — preferred
2. **Local open-source models** (local weights, no API) — if ML is genuinely needed
3. **Free hosted models** (rate-limited free tiers, no spend) — only if local is insufficient
4. **Paid APIs** — ONLY with explicit human approval before any call is made

Do not skip a lower tier to use a higher one. Do not pre-emptively assume a paid
API is required.

## Cost Gate Thresholds

Every execution is classified against its **actual API spend** (USD):

|| Gate | Condition | Meaning |
||------|-----------|---------|
|| `FREE_GO` | Cost == $0.00 | No API spend. Preferred outcome. |
|| `GO` | $0.01 – $0.49 inclusive | Trivial spend, auto-approved. |
|| `WARN_GO` | $0.50 – $1.00 inclusive | Moderate spend, flagged for review. |
|| `NO_GO` | > $1.00 | Blocked. Requires explicit approval before proceeding. |

Boundary convention: at exactly $0.50 the gate is `GO`; at exactly $1.00 the
gate is `WARN_GO`; anything above $1.00 is `NO_GO`.

The **default gate assumption is `FREE_GO`**. A task is only upgraded to a paid
gate when API spend actually occurs.

## Mandatory Gate Report Fields

Every gate report MUST include all four of the following:

- **Estimated API Cost** — predicted API spend before execution (USD)
- **Actual API Cost** — measured API spend after execution (USD)
- **Local Compute Used** — did the task rely on local compute? (Yes / No)
- **Fully Local Execution** — was the task completed with zero API calls? (Yes / No)

For the standard Malt Radar pipeline these default to `Estimated API Cost: $0.00`,
`Actual API Cost: $0.00`, `Local Compute Used: Yes`, `Fully Local Execution: Yes`.

The most desirable outcome is a **fully local execution with zero API cost**
(`FREE_GO`). Every paid-tier choice must be justified against this baseline.
