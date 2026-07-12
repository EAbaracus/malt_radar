# Malt Radar Agent Operating Instructions

## Mission

Maintain and improve Malt Radar while preserving data quality,
traceability, correctness, and evidence-based validation.

## Default Mode

Start in read-only mode.

Never assume modifications are required.

Inspect before acting.

## Evidence Requirements

Every important conclusion must be supported by evidence.

Never trust aggregate parser metrics alone.

Validate using source material whenever possible.

## Validation Requirements

Require:

- traceability
- random sampling
- source verification
- cross-page validation

## Database Safety

Before modifying a database:

1. create backup
2. inspect impact
3. apply change
4. verify results

## Completion Requirements

Before reporting success:

- verify outputs
- verify consistency
- check git status
- check validation results

## Product Rule

Price information may exist in storage.

Price information must never be exposed in UI or API.

## Escalation Rule

When confidence is low:

- stop
- explain uncertainty
- request additional verification
