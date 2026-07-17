#!/usr/bin/env python3
"""P103 CORPUS AUDIT — METADATA + DUP-DETECTION ENRICHMENT (read-only).
Adds to each record: full sha256, title/author/year/isbn (from embedded
EPUB/PDF metadata or filename parse), and dup_group. Writes corpus_audit_enriched.json.
Does NOT modify production.db / knowledge.db.
"""
import os, json, re, hashlib, sqlite3
from pathlib import Path

BASE = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
OUT  = BASE / "mr-kep" / "p103_corpus_audit"
RAW  = json.load(open(OUT/"corpus_audit_raw.json"))
KDB  = BASE / "mr-kep" / "p102_bootstrap" / "knowledge.db"

import fitz
from ebooklib import epub

def full_sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

ISBN_RE = re.compile(r'(97[89][\d][\d\s-]{8,14}\d)')
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')

def metadata_epub(path):
    out = {}
    try:
        b = epub.read_epub(str(path))
        t = b.get_metadata('DC', 'title');  out['title'] = t[0][0] if t else None
        a = b.get_metadata('DC', 'creator'); out['author'] = a[0][0] if a else None
        d = b.get_metadata('DC', 'date');    out['year'] = (d[0][0][:4] if d else None)
        ids = b.get_metadata('DC', 'identifier')
        for _, v in ids:
            if v and ISBN_RE.search(v[0]): out['isbn'] = ISBN_RE.search(v[0]).group(1).replace("-","")
    except Exception as e:
        out['err'] = str(e)
    return out

def metadata_pdf(path):
    out = {}
    try:
        doc = fitz.open(str(path))
        m = doc.metadata or {}
        out['title'] = m.get('title') or None
        out['author'] = m.get('author') or None
        # year + isbn from first 6 pages text
        txt = ""
        for i in range(min(6, len(doc))):
            try: txt += doc[i].get_text()
            except Exception: pass
        doc.close()
        ym = YEAR_RE.findall(txt)
        yrs = [int(y+"00"[0]+y) for y,_ in []]  # placeholder
        yrs = [int(y) for y,_ in YEAR_RE.findall(txt)]
        out['year'] = str(max(yrs)) if yrs else None
        im = ISBN_RE.search(txt)
        out['isbn'] = im.group(1).replace("-","") if im else None
    except Exception as e:
        out['err'] = str(e)
    return out

def parse_filename(fn):
    out = {}
    # year in parens
    ym = re.search(r'\((\d{4})', fn)
    if ym: out['year'] = ym.group(1)
    # "Last, First - Title"
    am = re.search(r'^([A-Z][\w\'-]+(?:\s+[A-Z][\w\'-]+)*)\s*,\s*([A-Z][\w\'-]+(?:\s+[A-Z][\w\'-]+)*)\s*-\s*(.+?)(?:\s*\(|\s*_)', fn)
    if am:
        out['author'] = f"{am.group(2)} {am.group(1)}"
        out['title'] = am.group(3).strip().rstrip('_').replace('_',' ')
    # libgen "[Title] - (year) - libgen.li"
    lm = re.search(r'\[(.+?)\]\s*-\s*\((\d{4})\)', fn)
    if lm and 'title' not in out:
        out['title'] = lm.group(1).strip()
        out['year'] = lm.group(2)
    im = ISBN_RE.search(fn)
    if im: out['isbn'] = im.group(1).replace("-","")
    return out

for rec in RAW:
    p = BASE / rec['path']
    if not p.is_file():  # skip aggregate/dir records (e.g. SMWS group) and missing
        rec['meta_source'] = 'non-file'; continue
    rec['sha256_full'] = full_sha256(p)
    fn = rec['filename']
    meta = {}
    if rec['format'] == 'epub':
        meta = metadata_epub(p)
    elif rec['format'] == 'pdf':
        meta = metadata_pdf(p)
    # filename fallback
    fm = parse_filename(fn)
    for k in ('title','author','year','isbn'):
        if not meta.get(k) and fm.get(k):
            meta[k] = fm[k]
    rec['title']  = meta.get('title') or None
    rec['author'] = meta.get('author') or None
    rec['year']   = meta.get('year') or None
    rec['isbn']   = meta.get('isbn') or None
    rec['meta_source'] = ('embedded' if (rec.get('title') and rec.get('title') not in fn)
                          else 'filename')

# duplicate detection: full sha256 identical -> dup group; same size + similar name -> suspect
by_hash = {}
for rec in RAW:
    by_hash.setdefault(rec.get('sha256_full'), []).append(rec)
dup_id = 0
for h, group in by_hash.items():
    if len(group) > 1 and h:
        dup_id += 1
        for rec in group:
            rec['dup_group'] = f"DUP-{dup_id}"
            rec['dup_note'] = f"identical SHA256 ({h[:12]}…) with {len(group)} copies"
# same size, different hash, high name similarity -> overlap suspect
import difflib
def norm(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
size_groups = {}
for rec in RAW:
    if rec.get('size_bytes'):
        size_groups.setdefault(rec['size_bytes'], []).append(rec)
for sz, group in size_groups.items():
    if len(group) > 1:
        names = [r['filename'] for r in group]
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                # exact dup already handled by hash group; here flag near-dups
                if group[i].get('dup_group') or group[j].get('dup_group'):
                    continue
                ratio = difflib.SequenceMatcher(None, names[i].lower(), names[j].lower()).ratio()
                if ratio >= 0.85:
                    group[i].setdefault('dup_note', '')
                    group[j].setdefault('dup_note', '')
                    tag = f" | size+name near-dup (ratio={ratio:.2f}) with {names[j][:40]}"
                    group[i]['dup_note'] += tag
                    group[j]['dup_note'] += f" | size+name near-dup (ratio={ratio:.2f}) with {names[i][:40]}"

json.dump(RAW, open(OUT/"corpus_audit_enriched.json","w"), indent=2, default=str)
dups = [r for r in RAW if r.get('dup_group')]
print(f"records={len(RAW)} | exact-duplicate groups={dup_id} | files in dup groups={len(dups)}")
for r in dups:
    print(f"  {r['dup_group']}: {r['filename'][:50]}  ({r['size_bytes']} bytes)")
# overlap suspects by size
sus = [r for r in RAW if 'size-match overlap' in (r.get('dup_note') or '')]
print(f"size-overlap suspects={len(sus)}")
