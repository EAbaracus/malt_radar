import sqlite3
import time
import os

def split_casks(cask_str):
    if not cask_str: return []
    import re
    parts = re.split(r'[&,\/;]+', cask_str)
    return [p.strip() for p in parts if p.strip()]

def run_benchmark():
    db_path = "bench_db.sqlite"
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
    CREATE TABLE cask_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    ''')
    cursor.execute('''
    CREATE TABLE whisky_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE product_cask_types (
        product_id INTEGER,
        cask_type_id INTEGER,
        PRIMARY KEY(product_id, cask_type_id)
    )
    ''')

    def get_or_create_cask_type(name):
        if not name: return None
        cursor.execute("SELECT id FROM cask_types WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row: return row[0]
        cursor.execute("INSERT INTO cask_types (name) VALUES (?)", (name,))
        return cursor.lastrowid

    # Mock data
    products = []
    for i in range(5000):
        # some duplicate cask types
        cask_str = "Sherry, Bourbon, Oak, Refill" if i % 2 == 0 else "Sherry, Port"
        products.append({"id": i+1, "cask_type": cask_str})
        cursor.execute("INSERT INTO whisky_products (id, name) VALUES (?, ?)", (i+1, f"Product {i}"))

    conn.commit()

    # Measure original method
    start_time = time.time()
    for row in products:
        product_id = row['id']
        casks = split_casks(row.get('cask_type'))
        for c in casks:
            cid = get_or_create_cask_type(c)
            cursor.execute("SELECT 1 FROM product_cask_types WHERE product_id=? AND cask_type_id=?", (product_id, cid))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO product_cask_types (product_id, cask_type_id) VALUES (?, ?)", (product_id, cid))
    conn.commit()
    end_time = time.time()
    original_time = end_time - start_time
    print(f"Original logic time: {original_time:.4f} seconds")

    # Measure optimized method (we will manually run this part to test the improvement on the same logic structure)
    # Clear the linking table
    cursor.execute("DELETE FROM product_cask_types")
    conn.commit()

    start_time = time.time()
    for row in products:
        product_id = row['id']
        casks = split_casks(row.get('cask_type'))

        cask_tuples = []
        for c in casks:
            cid = get_or_create_cask_type(c)
            if cid:
                cask_tuples.append((product_id, cid))
        if cask_tuples:
            cursor.executemany("INSERT OR IGNORE INTO product_cask_types (product_id, cask_type_id) VALUES (?, ?)", cask_tuples)

    conn.commit()
    end_time = time.time()
    optimized_time = end_time - start_time
    print(f"Optimized logic time: {optimized_time:.4f} seconds")

    print(f"Speedup: {original_time / optimized_time:.2f}x")

    conn.close()

if __name__ == "__main__":
    run_benchmark()
