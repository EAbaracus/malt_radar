from __future__ import annotations
import hashlib, json, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

DB = Path(r'C:\Users\eltun\Documents\malt radar CLEAN\output\import\production.db')
LOG = Path(r'C:\Users\eltun\Documents\malt radar CLEAN\docs\superpowers\specs\incident-2026-08-14\stability_observation.jsonl')
STATE = Path(r'C:\Users\eltun\Documents\malt radar CLEAN\docs\superpowers\specs\incident-2026-08-14\stability_observation_state.json')
INTERVAL_SECONDS = 3600
SAMPLES = 25


def sha256_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data):
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def table_digest(conn, table):
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]
    row_hashes = []
    for row in conn.execute(f'SELECT * FROM "{table}"'):
        row_hashes.append(sha256_bytes(json.dumps({cols[i]: row[i] for i in range(len(cols))}, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')))
    row_hashes.sort()
    h = hashlib.sha256()
    for rh in row_hashes:
        h.update(rh.encode('ascii'))
        h.update(b'\n')
    return h.hexdigest()


def snapshot(sample):
    before = sha256_file(DB)
    uri = 'file:' + quote(str(DB).replace('\\', '/'), safe='/:?') + '?mode=ro'
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.row_factory = sqlite3.Row
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        table_state = {}
        for table in tables:
            count_row = conn.execute(f'SELECT COUNT(*) AS c FROM "{table}"').fetchone()
            table_state[table] = {'rows': count_row[0], 'digest': table_digest(conn, table)}
        act = "(superseded_by IS NULL OR superseded_by='')"
        candidates = {}
        for column in ('country', 'region'):
            rows = conn.execute(
                f"SELECT w.whisky_id FROM whiskies w JOIN distilleries d ON d.distillery_id=w.distillery_id "
                f"WHERE {act} AND (w.{column} IS NULL OR w.{column}='') AND d.{column} IS NOT NULL AND d.{column}!='' ORDER BY w.whisky_id"
            ).fetchall()
            ids = '\n'.join(r[0] for r in rows)
            candidates[column] = {'count': len(rows), 'set_sha256': sha256_bytes(ids.encode('utf-8'))}
        record = {
            'sample': sample,
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'sha256_before_ro': before,
            'journal_mode': conn.execute('PRAGMA journal_mode').fetchone()[0],
            'integrity_check': conn.execute('PRAGMA integrity_check').fetchone()[0],
            'fk_violations': len(conn.execute('PRAGMA foreign_key_check').fetchall()),
            'table_state': table_state,
            'candidate_state': candidates,
        }
    finally:
        conn.close()
    record['sha256_after_ro'] = sha256_file(DB)
    st = DB.stat()
    record['size'] = st.st_size
    record['mtime_ns'] = st.st_mtime_ns
    record['read_changed_sha'] = record['sha256_before_ro'] != record['sha256_after_ro']
    record['wal'] = {'exists': (DB.with_suffix(DB.suffix + '-wal')).exists()}
    record['shm'] = {'exists': (DB.with_suffix(DB.suffix + '-shm')).exists()}
    record['journal'] = {'exists': (DB.with_suffix(DB.suffix + '-journal')).exists()}
    return record


if __name__ == '__main__':
    LOG.unlink(missing_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps({'started_utc': started, 'samples_required': SAMPLES, 'interval_seconds': INTERVAL_SECONDS, 'status': 'running', 'log': str(LOG)}, indent=2) + '\n', encoding='utf-8')
    for sample in range(SAMPLES):
        record = snapshot(sample)
        with LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')
        if sample + 1 < SAMPLES:
            time.sleep(INTERVAL_SECONDS)
    state = {'started_utc': started, 'completed_utc': datetime.now(timezone.utc).isoformat(), 'samples_required': SAMPLES, 'samples_collected': SAMPLES, 'interval_seconds': INTERVAL_SECONDS, 'status': 'complete', 'log': str(LOG)}
    STATE.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(state, ensure_ascii=False))
