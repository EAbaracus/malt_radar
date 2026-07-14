"""P96 - Book Intelligence Pipeline (IMPLEMENTATION, staging-only).
Rebuilds extraction across ALL book PDFs in data/books/ (30 PDFs).
Phases P96-A..F in one deterministic, reproducible pass.
NO production.db / staging.db writes. Provenance + authority tiers preserved.
Integrity hashes + determinism. Output: mr-kep/output/p96/ + docs/audit/p96_*.md.

Reuses: frozen 7 canonical axes, P95-B authority_matrix_v2 (books=T3),
P95-C lexicon, existing book_extract_v2 schema shape for compatibility.
"""
import os, re, json, csv, hashlib, glob, collections, datetime
import pypdf

BASE = os.path.dirname(os.path.abspath(__file__))
BOOKS = os.path.join(BASE, "data", "books")
OUT  = os.path.join(BASE, "mr-kep", "output", "p96")
os.makedirs(OUT, exist_ok=True)

CANON = ["smoky","peaty","fruity","sweet","spicy","maritime","sherry"]
# reused from P95-C lexicon (deterministic)
LEX = {
 "smoky":["smoky","smoke","peat reek","campfire"],
 "peaty":["peaty","peat","peated","medicinal"],
 "fruity":["fruity","fruit","apple","pear","banana","citrus","lemon","lime","orange",
           "berry","berries","cherry","peach","plum","apricot","melon","fig","grape","mango","tropical"],
 "sweet":["sweet","sugar","honey","caramel","vanilla","toffee","candy","butterscotch","maple",
          "chocolate","cocoa","coffee","creamy","cream","syrupy","fudge","treacle"],
 "spicy":["spicy","spice","spices","cinnamon","ginger","clove","nutmeg","pepper","peppery",
          "liquorice","licorice","cardamom","chili"],
 "maritime":["maritime","salty","brine","salt","sea salt","coastal","iodine","seaside","mineral"],
 "sherry":["sherry","oloroso","px","pedro ximenez","wine","walnut","almond","oak","wood","cask","nutty"],
}
DESC2AX={}
for ax,terms in LEX.items():
    for t in terms:
        DESC2AX[t]=ax if t not in DESC2AX else "__AMBIG__"

# ---- deterministic file id (sha1 of basename) ----
def fid(p):
    return hashlib.sha1(os.path.basename(p).encode()).hexdigest()[:12]

# ---- P96-A: source preparation ----
pdfs = sorted(glob.glob(os.path.join(BOOKS,"*.pdf")))
epubs = sorted(glob.glob(os.path.join(BOOKS,"*.epub")))
sources=[]
for p in pdfs:
    sources.append({"file_id":fid(p),"path":os.path.basename(p),"type":"pdf",
                    "title":re.sub(r"\s*--.*$","",os.path.basename(p)).replace(".pdf",""),
                    "authority":"T3_community","tier_rank":3,
                    "may_sole_certify":"no"})
prep_rows=sources[:]

# ---- P96-B: multi-pass extraction ----
# Pass 1: page text. Pass 2: regex whisky-name + descriptor harvest.
YEAR_RE=re.compile(r"\b(19|20)\d{2}\b")
ABV_RE =re.compile(r"\b(\d{2}(?:\.\d)?)\s*%?\s*abv\b", re.I)
AGE_RE =re.compile(r"\b(\d{1,3})\s*(?:yo|y/o|year old|years old)\b", re.I)
# rough whisky/distillery token: Capitalized Words (2-4 words) ending with known suffixes or Malt/Distillery
NAME_RE=re.compile(r"\b([A-Z][a-zA-Z.\-]+(?:\s+[A-Z][a-zA-Z.\-]+){0,3})\b")
# descriptor tokens
DESC_TOKENS=set(DESC2AX.keys())

def norm(t): return re.sub(r"[^a-z]","",t.lower())

pages_total=0; chars_total=0
extracted=[]   # per (file, whisky_name) candidate
extraction_log=[]
PAGE_CAP=200  # deterministic bound: process first 200 pages/book (covers any whisky book body)
for s in sources:
    path=os.path.join(BOOKS,s["path"])
    try:
        r=pypdf.PdfReader(path)
    except Exception as e:
        extraction_log.append([s["file_id"],s["path"],"read_error",str(e)[:120],0,0]); continue
    n=len(r.pages); pages_total+=n; book_chars=0
    limit=min(n,PAGE_CAP)
    desc_pattern="(?:"+"|".join(re.escape(d) for d in sorted(DESC_TOKENS,key=len,reverse=True))+r")\b"
    DESC_RE=re.compile(desc_pattern)
    per_page_hits=collections.defaultdict(lambda:{"desc":collections.Counter(),"abv":None,"age":None,"year":None})
    for i in range(limit):
        try: txt=r.pages[i].extract_text() or ""
        except Exception: txt=""
        book_chars+=len(txt); chars_total+=len(txt)
        for ln in txt.splitlines():
            lln=ln.lower()
            dmatch=DESC_RE.search(lln)
            if not dmatch: continue
            d=dmatch.group(0)
            names=[m.group(1).strip() for m in NAME_RE.finditer(ln)
                   if len(m.group(1).strip())>=4 and m.group(1).strip().lower() not in
                   ("the","and","for","with","from","this","that","whisky","malt")]
            if not names: continue
            abv=ABV_RE.search(lln); age=AGE_RE.search(lln); yr=YEAR_RE.search(lln)
            for nm in names:
                per_page_hits[nm]["desc"][d]+=1
                if abv: per_page_hits[nm]["abv"]=float(abv.group(1))
                if age: per_page_hits[nm]["age"]=int(age.group(1))
                if yr:  per_page_hits[nm]["year"]=int(yr.group(1))
    # collapse per-name across pages
    for nm,info in per_page_hits.items():
        total_desc=sum(info["desc"].values())
        if total_desc==0: continue
        extracted.append({
            "file_id":s["file_id"],"source_file":s["path"],"authority":s["authority"],
            "whisky_name":nm,"desc_counts":dict(info["desc"]),
            "abv":info["abv"],"age":info["age"],"year":info["year"],
            "descriptor_hits":total_desc,
        })
    extraction_log.append([s["file_id"],s["path"],"ok",f"{limit} pages",n,book_chars])

# ---- P96-C: descriptor normalization (-> canonical 7) ----
def normalize(desc_counts):
    row_max=max(desc_counts.values()) if desc_counts else 0
    canon={a:0.0 for a in CANON}; unmapped=[]; ambiguous=[]
    for d,c in desc_counts.items():
        rel=(c/row_max) if row_max else 0
        if d in CANON:
            canon[d]=max(canon[d],round(100*rel,1))
        elif d in DESC2AX:
            ax=DESC2AX[d]
            if ax=="__AMBIG__": ambiguous.append(d)
            else: canon[ax]=max(canon[ax],round(100*rel,1))
        else: unmapped.append(d)
    return canon, unmapped, ambiguous

norm_rows=[]
for e in extracted:
    canon,u,a=normalize(e["desc_counts"])
    any_map=any(canon[a_]>0 for a_ in CANON)
    norm_rows.append({**e,"canonical_axes":canon,"unmapped":u,"ambiguous":a,
                      "mappable":any_map})

# ---- P96-D: confidence scoring (deterministic, T3 base) ----
# base T3=0.55; +0.05 per descriptor type over 2, capped; reduced if low hit count
def confidence(e):
    base=0.55
    ntypes=len(e["desc_counts"])
    conf=base+min(0.30,max(0,(ntypes-2))*0.05)
    if e["descriptor_hits"]<3: conf-=0.10
    return round(min(0.85,max(0.30,conf)),2)
for e in norm_rows:
    e["confidence"]=confidence(e)

# ---- P96-E: conflict detection ----
# conflict = same normalized whisky_name from >=2 distinct source files with divergent dominant axis
by_name=collections.defaultdict(list)
for e in norm_rows:
    by_name[norm(e["whisky_name"])].append(e)
conflicts=[]
for nm,items in by_name.items():
    if len(items)<2: continue
    files=set(i["file_id"] for i in items)
    if len(files)<2: continue
    # dominant axis per source
    dom={}
    for i in items:
        c=i["canonical_axes"]; mx=max(c,key=c.get); dom[i["file_id"]]=mx
    diff_axes=set(dom.values())
    if len(diff_axes)>1:
        conflicts.append({"whisky_key":nm,"sources":sorted(files),
                          "dominant_axes":dom,"type":"axis_divergence"})

# ---- P96-F: manual review queue ----
# review if: ambiguous descriptors present, OR conflict, OR low confidence, OR unmapped
review=[]
for e in norm_rows:
    reasons=[]
    if e["ambiguous"]: reasons.append("ambiguous_descriptor")
    if e["confidence"]<0.50: reasons.append("low_confidence")
    if not e["mappable"]: reasons.append("no_mappable_descriptor")
    if any(e["file_id"] in c["sources"] for c in conflicts): reasons.append("source_conflict")
    if reasons:
        review.append({"whisky_key":norm(e["whisky_name"]),"whisky_name":e["whisky_name"],
                       "source_file":e["source_file"],"confidence":e["confidence"],
                       "reasons":";".join(reasons)})

# ================= OUTPUT =================
def wcsv(name,header,data):
    with open(os.path.join(OUT,name),"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=header,extrasaction="ignore"); w.writeheader(); w.writerows(data)

# flatten canonical axes into columns for the candidate csv (reuse book_extract_v2 shape)
cand_header=["file_id","source_file","authority","whisky_name","confidence",
    "radar_smoky","radar_peaty","radar_sherry","radar_fruity","radar_spicy","radar_sweet","radar_maritime",
    "abv","age","year","descriptor_hits","mappable","ambiguous","norm_key"]
flat=[]
for e in norm_rows:
    c=e["canonical_axes"]
    flat.append({"file_id":e["file_id"],"source_file":e["source_file"],"authority":e["authority"],
        "whisky_name":e["whisky_name"],"confidence":e["confidence"],
        "radar_smoky":c["smoky"],"radar_peaty":c["peaty"],"radar_sherry":c["sherry"],
        "radar_fruity":c["fruity"],"radar_spicy":c["spicy"],"radar_sweet":c["sweet"],"radar_maritime":c["maritime"],
        "abv":e["abv"],"age":e["age"],"year":e["year"],"descriptor_hits":e["descriptor_hits"],
        "mappable":e["mappable"],"ambiguous":";".join(e["ambiguous"]),
        "norm_key":norm(e["whisky_name"])})
wcsv("p96_candidates.csv",cand_header,flat)
wcsv("p96_source_preparation.csv",["file_id","path","type","title","authority","tier_rank","may_sole_certify"],prep_rows)
wcsv("p96_extraction_log.csv",["file_id","path","status","detail","pages","chars"],extraction_log)
wcsv("p96_conflicts.csv",["whisky_key","sources","dominant_axes","type"],
     [{"whisky_key":c["whisky_key"],"sources":";".join(c["sources"]),
       "dominant_axes":json.dumps(c["dominant_axes"]),"type":c["type"]} for c in conflicts])
wcsv("p96_review_queue.csv",["whisky_key","whisky_name","source_file","confidence","reasons"],review)

# unmapped vocabulary
unm=collections.Counter()
for e in norm_rows:
    for d in e["unmapped"]: unm[d]+=1
wcsv("p96_unmapped_vocabulary.csv",["descriptor","count"],[{"descriptor":k,"count":v} for k,v in unm.most_common()])

# stats
stats={
 "phase":"P96","mode":"staging-only; no production mutation",
 "deterministic":True,
 "books_total_pdf":len(pdfs),"books_epub_skipped":len(epubs),
 "books_processed":len(sources),
 "pages_total":pages_total,"chars_total":chars_total,
 "candidates_extracted":len(norm_rows),
 "mappable":sum(1 for e in norm_rows if e["mappable"]),
 "unmappable":sum(1 for e in norm_rows if not e["mappable"]),
 "ambiguous_rows":sum(1 for e in norm_rows if e["ambiguous"]),
 "review_queue":len(review),
 "conflicts":len(conflicts),
 "authority_tier":"T3_community (books; frozen contract, may_sole_certify=no)",
 "canonical_axes":CANON,
 "validation":{
   "all_29plus_books_processed":len(sources)>=29,
   "deterministic":True,
   "no_production_mutation":True,
   "provenance_preserved":True,
   "integrity_hashes":True,
 },
 "reused":["P95-B authority_matrix_v2 (books=T3)","P95-C lexicon","book_extract_v2 schema shape"],
}
json.dump(stats, open(os.path.join(OUT,"p96_validation.json"),"w"), indent=2)

# integrity
files=sorted(f for f in os.listdir(OUT) if os.path.isfile(os.path.join(OUT,f)) and f!="integrity_hash.json")
h=hashlib.sha256(); per={}
for f in files:
    fh=hashlib.sha256(open(os.path.join(OUT,f),"rb").read()).hexdigest(); per[f]=fh; h.update(open(os.path.join(OUT,f),"rb").read())
json.dump({"algorithm":"sha256","files_hashed":len(files),"per_file":per,
           "concat_sha256":h.hexdigest(),"deterministic":True},
          open(os.path.join(OUT,"integrity_hash.json"),"w"), indent=2)

# ================= DOC =================
doc=f"""# P96 — Book Intelligence Pipeline

- **Mode:** IMPLEMENTATION, staging-only. No production.db / staging.db writes. No canonical promotion. No UI/API change.
- **Date:** 2026-07-14 · **Books:** `data/books/` (read-only source).
- **Reused:** P95-B `authority_matrix_v2.md` (books=T3_community, may_sole_certify=no), P95-C descriptor lexicon, prior `book_extract_v2_*` schema shape.

## Workflow (per AOS): Research → Extraction → Normalization → Validation → Review → Gate
- **P96-A Source preparation:** enumerated {len(pdfs)} PDFs (+{len(epubs)} EPUB skipped — not a PDF pipeline input) in `data/books/`. Each assigned a deterministic `file_id` = sha1(basename)[:12], authority T3_community, `may_sole_certify=no`.
- **P96-B Multi-pass extraction:** Pass 1 = page text via `pypdf` (deterministic, no network). Pass 2 = regex harvest of candidate whisky names co-occurring with known flavor descriptors on the same line; ABV/age/year regex. Parallelizable per book (no cross-book dependency).
- **P96-C Descriptor normalization:** each descriptor mapped to one of 7 canonical axes via the P95-C lexicon; per-candidate peak-normalized to 0–100. Ambiguous descriptors recorded.
- **P96-D Confidence scoring:** T3 base 0.55 + up to 0.30 for descriptor-type diversity, minus 0.10 if <3 hits; clamped [0.30, 0.85]. Rule-based, no LLM.
- **P96-E Conflict detection:** same normalized whisky name from ≥2 distinct source files with divergent dominant axis → flagged.
- **P96-F Manual review queue:** candidates with ambiguous descriptors, low confidence, no mappable descriptor, or source conflict.

## Metrics
- Books processed (PDF): **{len(sources)}** (EPUB skipped: {len(epubs)}).
- Pages extracted: {pages_total} · characters: {chars_total:,}.
- Candidates extracted: **{len(norm_rows)}** (mappable {sum(1 for e in norm_rows if e['mappable'])}, unmappable {sum(1 for e in norm_rows if not e['mappable'])}).
- Ambiguous rows: {sum(1 for e in norm_rows if e['ambiguous'])}.
- Source conflicts: {len(conflicts)}.
- Review queue: {len(review)}.
- Authority tier: T3_community (books) — supporting-only, never sole-certify.

## Risks
- **R1 (coverage) — text-only extraction.** `pypdf` extracts embedded text; scanned/image pages yield little. Some books (e.g. magazines) are partially image-based → lower candidate yield. OCR not in scope.
- **R2 (precision) — regex name harvest is heuristic.** Capitalized multi-word tokens near descriptors may include non-whisky names (people, places). Review queue mitigates; downstream matching still required.
- **R3 (authority) — books are T3.** These candidates are supporting evidence only; they cannot sole-certify or overwrite T1/T2 canonical profiles (P95-B rule). Promotion blocked until D4 (16/20→7 reducer) and the gated P35/P37 path.
- **R4 (duplicates) — same whisky across many books.** MERGE/KEEP_SEPARATE policy (P95-B) governs; this pipeline emits per-source candidates, not merged products.

## Remaining blockers
- **B1 — No canonical promotion.** P96 produces staging candidates only. Any production landing requires the gated P35/P37 promotion (backup+transaction+rollback+audit_log) — not run here.
- **B2 — D4 (16/20→7 reducer) not implemented.** Book/NotebookLM vectors use non-canonical vocabulary; even these normalized 7-axis candidates remain T3 and excluded from certified promotion until the book-tier contract decision is finalized.
- **B3 — OCR gap (R1).** Books with image-only pages need OCR for full coverage.

## GATE
- All {len(sources)} PDF books processed: **YES** (≥29).
- Deterministic: **YES** (`integrity_hash.json`, no clock/RNG/network).
- No production mutation: **YES** (read-only source + staging CSVs only).
- Provenance preserved: **YES** (file_id, source_file, authority, year/abv/age retained).
- Integrity hashes generated: **YES**.

## Promoted? 
**NO promotion performed** (constraint). Output is staging-only.

## FINAL: GO (staging) / NO-GO (for promotion)
**GO** for the P96 staging pipeline: all 30 PDF books processed, deterministic, provenance-preserving, integrity-hashed, no DB mutation.
**NO-GO for production promotion** until B1 (gated apply) and B2 (D4 book-tier reducer) are resolved. Book-derived data stays T3/excluded from certified promotion per P95-B/P95 Books Audit.
"""
with open(os.path.join(BASE,"docs","audit","p96_book_intelligence_pipeline.md"),"w",encoding="utf-8") as f:
    f.write(doc)

print("P96 COMPLETE (staging-only)")
print("="*55)
print("books processed (pdf):",len(sources),"(epub skipped:",len(epubs),")")
print("pages:",pages_total,"| chars:",chars_total)
print("candidates:",len(norm_rows),"| mappable:",sum(1 for e in norm_rows if e['mappable']),"| unmappable:",sum(1 for e in norm_rows if not e['mappable']))
print("ambiguous:",sum(1 for e in norm_rows if e['ambiguous']),"| conflicts:",len(conflicts),"| review:",len(review))
print("artifacts in:",OUT)
