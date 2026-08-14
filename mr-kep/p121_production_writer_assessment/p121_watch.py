import sqlite3, os, time, hashlib, urllib.parse

REPO = r"C:\Users\eltun\Documents\malt radar CLEAN"
DB = os.path.join(REPO, "output", "import", "production.db")
LOG = os.path.join(REPO, "mr-kep", "p121_production_writer_assessment", "p121_watch.log")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

uri = "file:" + urllib.parse.quote(DB.replace("\\", "/"), safe="/:") + "?mode=ro"

with open(LOG, "a") as log:
    for i in range(1, 13):
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        c = sqlite3.connect(uri, uri=True)
        n = c.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
        d = c.execute("SELECT COUNT(*) FROM distilleries").fetchone()[0]
        c.close()
        m = os.path.getmtime(DB)
        j = "J" if os.path.exists(DB + "-journal") else "-"
        w = "W" if os.path.exists(DB + "-wal") else "-"
        s = sha256(DB)
        line = (f"{t} sample {i:02d} count={n} distilleries={d} "
                f"mtime={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(m))} "
                f"journal={j}{w} sha256={s}\n")
        log.write(line)
        log.flush()
        if i < 12:
            time.sleep(300)
