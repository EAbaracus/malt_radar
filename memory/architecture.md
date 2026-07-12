# Architecture Memory

- **Database:** SQLite (`production.db`) containing distilleries, whiskies, tasting_notes, flavor_profiles, and price_history.
- **NLP Flavor Engine:** Uses anchor-guided regex pattern scanners (sliding window around flavor anchors) to assign ratings on 7 flavor dimensions.
- **Identity Resolver:** Employs string normalization and Levenshtein fuzzy matching to resolve new expressions to master products.
