import sqlite3
conn = sqlite3.connect('output/import/production.db')
print('flavor_profiles:', conn.execute('SELECT COUNT(*) FROM flavor_profiles').fetchone()[0])
print('p2_profiles:', conn.execute("SELECT COUNT(*) FROM flavor_profiles WHERE flavor_source LIKE 'p2_review_promotable%'").fetchone()[0])
print('fk_missing:', conn.execute('SELECT COUNT(*) FROM flavor_profiles fp LEFT JOIN whiskies w ON w.whisky_id=fp.whisky_id WHERE w.whisky_id IS NULL').fetchone()[0])
print('duplicate_profiles:', conn.execute('SELECT COUNT(*) FROM (SELECT whisky_id, flavor_source, COUNT(*) c FROM flavor_profiles GROUP BY whisky_id, flavor_source HAVING c > 1)').fetchone()[0])
conn.close()