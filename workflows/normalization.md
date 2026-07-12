# Normalization Workflow

1. **String Cleaning:** Strip whitespace, lowercase names, and remove extra spaces.
2. **ABV Cleaning:** Extract decimals, strip "%" symbols, and cast to Float.
3. **Age Cleaning:** Standardize "yo", "years old" to numerical format or "NAS" for No Age Statement.
4. **Distillery Matching:** Perform fuzzy match against the master company/distillery dictionary.
