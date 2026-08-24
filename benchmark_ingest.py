import sqlite3
import time
import os

# Set up test database
db_path = "test_perf.db"
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# create basic schema
cursor.execute("""
CREATE TABLE IF NOT EXISTS flavor_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS product_flavor_tags (
    product_id INTEGER,
    flavor_tag_id INTEGER,
    PRIMARY KEY(product_id, flavor_tag_id)
);
""")
conn.commit()

class DummyReport:
    inserted_countries = 0
    inserted_regions = 0
report = DummyReport()

def get_or_create_flavor_tag_local(name):
    if not name: return None
    cursor.execute("SELECT id FROM flavor_tags WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row: return row[0]
    cursor.execute("INSERT INTO flavor_tags (name) VALUES (?)", (name,))
    return cursor.lastrowid

# Generate a bunch of products and flavor tags
products_and_flavors = []
for p_id in range(1, 10000):
    flavors = [f"flavor_{i}" for i in range(p_id % 5 + 1)] + ["common_flavor1", "common_flavor2"]
    products_and_flavors.append((p_id, flavors))


start_time = time.time()

# This simulates the current implementation
for product_id, flavors in products_and_flavors:
    for f in set(flavors):
        fid = get_or_create_flavor_tag_local(f)
        cursor.execute("SELECT 1 FROM product_flavor_tags WHERE product_id=? AND flavor_tag_id=?", (product_id, fid))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO product_flavor_tags (product_id, flavor_tag_id) VALUES (?, ?)", (product_id, fid))

end_time = time.time()
print(f"Time taken (N+1 approach): {end_time - start_time:.4f} seconds")

# Clear tables for second benchmark
cursor.execute("DELETE FROM product_flavor_tags")
cursor.execute("DELETE FROM flavor_tags")
conn.commit()

start_time2 = time.time()
# Simulates using INSERT OR IGNORE
for product_id, flavors in products_and_flavors:
    for f in set(flavors):
        fid = get_or_create_flavor_tag_local(f)
        cursor.execute("INSERT OR IGNORE INTO product_flavor_tags (product_id, flavor_tag_id) VALUES (?, ?)", (product_id, fid))

end_time2 = time.time()
print(f"Time taken (INSERT OR IGNORE approach): {end_time2 - start_time2:.4f} seconds")


# Clear tables for third benchmark
cursor.execute("DELETE FROM product_flavor_tags")
cursor.execute("DELETE FROM flavor_tags")
conn.commit()

start_time3 = time.time()
# Simulates using executemany with INSERT OR IGNORE
for product_id, flavors in products_and_flavors:
    f_set = set(flavors)
    if not f_set:
        continue
    fids = [get_or_create_flavor_tag_local(f) for f in f_set]
    cursor.executemany("INSERT OR IGNORE INTO product_flavor_tags (product_id, flavor_tag_id) VALUES (?, ?)", [(product_id, fid) for fid in fids if fid is not None])

end_time3 = time.time()
print(f"Time taken (executemany INSERT OR IGNORE approach): {end_time3 - start_time3:.4f} seconds")


conn.close()
if os.path.exists(db_path):
    os.remove(db_path)
