# Phase 3 Scope and Rules

## Scope
Phase 3 establishes a robust Entity and Staging architecture for the Malt Radar project. It introduces separate master tables for Brands, Bottlers, Companies, and External Entities, removing the need to incorrectly overload the `distilleries` table. It also introduces `staging_` tables for incoming candidates (products, tasting notes, prices, external reviews) to hold them until manually approved, and `knowledge_` tables to store contextual reference data (regions, glossaries, guides).

## Core Rules
1. **No Overloading Distilleries**: Brand, bottler, and company records must be isolated into their respective entity tables. They will not be inserted as distilleries.
2. **Strict Staging Workflow**: New product candidates (e.g., from Whisky Edition API) must NOT be written directly to the `whiskies` table. They must land in `staging_new_products`.
3. **No Automatic Current Price Overwrites**: Malt List historical prices are bar menu pour prices (35ml) and must NEVER overwrite the `current_price` column in the `whiskies` table. They are routed to `staging_historical_menu_prices`.
4. **Tasting Note Integrity**: Whisky Edition tasting notes must not be imported into the production notes table until the corresponding new product is approved or mapped to an existing product. They will wait in `staging_tasting_notes`.
5. **Knowledge Data Protection**: WhiskeyFYI knowledge data (regions, glossary, guides) serves as reference context. It must never overwrite master product or distillery data.
6. **Mandatory Manual Approval**: All staging data requires a manual approval workflow (e.g., via `staging_manual_review_queue`) before promoting to production tables.
7. **Absolute Isolation**: During this design phase, production DB manipulation, migrations, imports, and patch executions are strictly forbidden.
