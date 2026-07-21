# 184 — Flavor Import SQL Preview

* SQL preview summary: Generated 1 inserts and 1 updates.
* Per-row planned action table:

| Whisky ID | Name | Planned Action | Target Table | Blocked Reason |
| --- | --- | --- | --- | --- |
| W000001 | aberlour a'bunadh | would_insert | flavor_profiles |  |
| W000042 | aberlour a'bunadh (batch 40) | would_update | flavor_profiles |  |
| W001485 | alberta premium dark horse | blocked | flavor_profiles | manual_review |
| W009999 | zero flavor whisky | blocked | flavor_profiles | zero_flavor_vector |

* Insert/update preview:

### W000001 — aberlour a'bunadh (would_insert)

```sql
INSERT INTO flavor_profiles (whisky_id, whisky_name, production_bottle_name, match_score, match_method, flavor_vector, flavor_profile, flavor_tags, flavor_source, flavor_data_confidence, production_price, production_rating, production_region, notes_for_review) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

**Parameters:**
`["W000001", "aberlour a'bunadh", "Aberlour A'Bunadh", 100, "exact", "{\"apple\": 18.0, \"sweet\": 5.0, \"wood\": 6.0}", "{\"fruity\": 18.0, \"sweet\": 5.0, \"spicy\": 0.0, \"smoky_peaty\": 0.0, \"oak_cask\": 6.0, \"malty_cereal\": 0.0, \"floral_herbal\": 0.0}", "[\"apple\", \"wood\", \"sweet\"]", "production_data.csv", "high", 80.0, 90.0, "Speyside", "Auto-matched securely"]`

### W000042 — aberlour a'bunadh (batch 40) (would_update)

```sql
UPDATE flavor_profiles SET whisky_name = ?, production_bottle_name = ?, match_score = ?, match_method = ?, flavor_vector = ?, flavor_profile = ?, flavor_tags = ?, flavor_source = ?, flavor_data_confidence = ?, production_price = ?, production_rating = ?, production_region = ?, notes_for_review = ? WHERE whisky_id = ?
```

**Parameters:**
`["aberlour a'bunadh (batch 40)", "Aberlour A'Bunadh (Batch 40)", 100, "exact", "{\"apple\": 28.0, \"sweet\": 23.0}", "{\"fruity\": 28.0, \"sweet\": 23.0, \"spicy\": 0.0, \"smoky_peaty\": 0.0, \"oak_cask\": 0.0, \"malty_cereal\": 0.0, \"floral_herbal\": 0.0}", "[\"apple\", \"sweet\"]", "production_data.csv", "high", 85.0, 92.0, "Speyside", "Auto-matched securely", "W000042"]`


* Blocked rows: W001485, W009999
* W001485 status: blocked (manual_review)
* production.db changed: NO
* Import executed: NO
