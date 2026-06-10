import csv
import os

MASTER_FILE = r"C:\Users\eltun\Documents\malt radar\recovered_from_radiant_bardeen\output\final\67_FINAL_import_ready_distilleries_whiskycom_enriched.csv"
HIGH_CONF_MATCHES = "15_distillery_high_confidence_matches.csv"
REF_DISTILLERY = "09_distillery_reference_candidates.csv"
REF_REGION = "10_region_reference.csv"
REF_GLOSSARY = "11_glossary_terms.csv"
REF_GUIDES = "12_guides_index.csv"

# 1. Load Master Distilleries
master_dist = {}
try:
    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            master_dist[row.get("UUID", "")] = row
except Exception as e:
    pass

# 2. Load Reference Distilleries
ref_dist = {}
try:
    with open(REF_DISTILLERY, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ref_dist[row["name"]] = row
except Exception as e:
    pass

# Process Audits
audit_rows = []
stats = {
    "total": 0,
    "fully_safe": 0,
    "has_overwrite_risk": 0,
    "link_only": 0,
    "desc_only": 0,
    "region_overwrite_risk": 0,
    "rejected": 0
}

try:
    with open(HIGH_CONF_MATCHES, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            stats["total"] += 1
            m_uuid = row["master_uuid"]
            r_name = row["ref_name"]
            score = row["best_score"]
            
            master = master_dist.get(m_uuid, {})
            ref = ref_dist.get(r_name, {})
            
            cur_url = master.get("Website", "")
            prop_url = ref.get("url", "")
            cur_desc = master.get("Description", "")
            prop_desc = ref.get("description", "")
            cur_reg = master.get("Region", "")
            prop_reg = ref.get("region", "")
            
            fields_to_fill = []
            fields_overwrite = []
            
            if prop_url:
                if not cur_url: fields_to_fill.append("url")
                elif cur_url != prop_url: fields_overwrite.append("url")
            
            if prop_desc:
                if not cur_desc: fields_to_fill.append("description")
                elif cur_desc != prop_desc: fields_overwrite.append("description")
                
            if prop_reg:
                if not cur_reg: fields_to_fill.append("region")
                elif cur_reg.lower() != prop_reg.lower(): fields_overwrite.append("region")
                
            safe = "YES" if not fields_overwrite and fields_to_fill else "NO"
            reason = ""
            if fields_overwrite:
                safe = "NO"
                reason = "Overwrite risk on: " + ", ".join(fields_overwrite)
                stats["has_overwrite_risk"] += 1
                if "region" in fields_overwrite:
                    stats["region_overwrite_risk"] += 1
                stats["rejected"] += 1
            elif not fields_to_fill:
                safe = "NO"
                reason = "No new data to add"
                stats["rejected"] += 1
            else:
                stats["fully_safe"] += 1
                if "url" in fields_to_fill and "description" not in fields_to_fill:
                    stats["link_only"] += 1
                elif "description" in fields_to_fill and "url" not in fields_to_fill:
                    stats["desc_only"] += 1
            
            audit_rows.append({
                "whiskeyfyi_name": r_name,
                "matched_master_distillery_id": m_uuid,
                "matched_master_name": master.get("Distillery", ""),
                "match_score": score,
                "current_master_url": cur_url,
                "proposed_whiskeyfyi_url": prop_url,
                "current_description": cur_desc,
                "proposed_description": prop_desc,
                "current_region": cur_reg,
                "proposed_region": prop_reg,
                "fields_to_fill": "|".join(fields_to_fill),
                "fields_that_would_overwrite": "|".join(fields_overwrite),
                "safe_to_apply": safe,
                "reason": reason
            })
except Exception as e:
    pass

with open("23_distillery_patch_field_level_audit.csv", "w", newline="", encoding="utf-8") as f:
    if audit_rows:
        writer = csv.DictWriter(f, fieldnames=audit_rows[0].keys())
        writer.writeheader()
        writer.writerows(audit_rows)
    else:
        f.write("whiskeyfyi_name,matched_master_distillery_id,matched_master_name,match_score,current_master_url,proposed_whiskeyfyi_url,current_description,proposed_description,current_region,proposed_region,fields_to_fill,fields_that_would_overwrite,safe_to_apply,reason\n")

# 24_distillery_patch_apply_or_reject_report.txt
report_24 = [
    "DISTILLERY PATCH APPLY OR REJECT REPORT",
    "=======================================",
    f"Toplam high-confidence: {stats['total']}",
    f"Dogrudan uygulanabilir kayit: {stats['fully_safe']}",
    f"Overwrite riski olan kayit: {stats['has_overwrite_risk']}",
    f"Sadece external link eklenebilir kayit: {stats['link_only']}",
    f"Description alani eklenebilir kayit: {stats['desc_only']}",
    f"Region/Country overwrite riski var mi? {'Evet' if stats['region_overwrite_risk'] > 0 else 'Hayir'} ({stats['region_overwrite_risk']} kayitta)",
    f"Uygulanmasi reddedilen kayitlar: {stats['rejected']} (Bkz. 23 nolu csv 'reason' kolonu)"
]
with open("24_distillery_patch_apply_or_reject_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report_24))

# 25_knowledge_tables_integration_plan.md
plan_25 = """# Knowledge Tables Integration Plan

Ayri knowledge/reference model onerisi:

## 1. knowledge_regions
* **Amac:** Uygulama ici bilgi ekranlarinda ve bolge detay sayfalarinda referans icerik saglamak.
* **Alanlar:** source, source_id, region_name, country, description, url, confidence

## 2. knowledge_glossary_terms
* **Amac:** Kullanicilara uygulama ici "Whisky Terimleri Sozlugu" sunmak.
* **Alanlar:** source, term, definition, category, url, confidence

## 3. knowledge_guides
* **Amac:** Urunlerle dogrudan eslesmeyen genel egitim, tadim rehberleri veya "nasil yapilir" iceriklerini referans olarak saklamak.
* **Alanlar:** source, title, slug, category, summary, url, import_recommendation

## 4. external_reference_links
* **Amac:** Master product/distillery verisini bozmadan dis baglantilari ve ek aciklamalari "external/reference metadata" olarak iliskisel (1-to-many) veya external schema'da saklamak.

*Onemli Not:* WhiskeyFYI description/url alanlari varsa yalnizca external/reference metadata olarak degerlendirilecek, mevcut dolu master alanlari ASLA overwrite edilmeyecektir. Production DB'ye dogrudan patch uygulanmayacak, ara knowledge table'lar uzerinden API'a sunulacaktir.
"""
with open("25_knowledge_tables_integration_plan.md", "w", encoding="utf-8") as f:
    f.write(plan_25)

# 26_regions_knowledge_import_preview.csv
reg_preview = []
try:
    with open(REF_REGION, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            reg_preview.append({
                "source": "whiskeyfyi",
                "source_id": row.get("slug", ""),
                "region_name": row.get("name", row.get("region", "")),
                "country": row.get("country", ""),
                "description": row.get("description", ""),
                "url": row.get("url", ""),
                "confidence": "high"
            })
except:
    pass
with open("26_regions_knowledge_import_preview.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["source", "source_id", "region_name", "country", "description", "url", "confidence"])
    writer.writeheader()
    writer.writerows(reg_preview)

# 27_glossary_knowledge_import_preview.csv
glos_preview = []
try:
    with open(REF_GLOSSARY, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            glos_preview.append({
                "source": "whiskeyfyi",
                "term": row.get("name", row.get("term", "")),
                "definition": row.get("description", row.get("definition", "")),
                "category": row.get("type_category", row.get("category", "")),
                "url": row.get("url", ""),
                "confidence": "high"
            })
except:
    pass
with open("27_glossary_knowledge_import_preview.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["source", "term", "definition", "category", "url", "confidence"])
    writer.writeheader()
    writer.writerows(glos_preview)

# 28_guides_reference_import_preview.csv
guides_preview = []
try:
    with open(REF_GUIDES, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            guides_preview.append({
                "source": "whiskeyfyi",
                "title": row.get("name", row.get("title", "")),
                "slug": row.get("slug", ""),
                "category": row.get("type_category", row.get("category", "")),
                "summary": row.get("description", row.get("summary", "")),
                "url": row.get("url", ""),
                "import_recommendation": "reference_only_no_product_link"
            })
except:
    pass
with open("28_guides_reference_import_preview.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["source", "title", "slug", "category", "summary", "url", "import_recommendation"])
    writer.writeheader()
    writer.writerows(guides_preview)

# 29_whiskeyfyi_final_decision_gate.txt
gate_29 = f"""WHISKEYFYI FINAL DECISION GATE
==============================
A) Distillery enrichment uygulanabilir mi?
-> {stats['fully_safe']} adet kayit GUVENLI olarak (mevcut veriyi bozmadan) URL ve Description icin zenginlestirilebilir. Kalan {stats['rejected']} kayit risk (overwrite) icerdigi veya yeni veri getirmedigi icin apply edilmemelidir.

B) Sadece knowledge tables import mu oneriliyor?
-> Evet. Region, Glossary ve Guide datalarinin product master yerine ayri "knowledge_*" tablolarina import edilmesi, mimari acidan en guvenli ve temiz yaklasimdir.

C) Hangi kayitlar manuel review gerektiriyor?
-> 23 nolu CSV'deki "safe_to_apply = NO" olan, ozellikle region veya description cakismasi (overwrite riski) bulunan kayitlar. Toplam {stats['rejected']} kayit manual review'de reddedilmis sayildi veya inceleme gerektiriyor.

D) Production'a girecek hicbir sey var mi?
-> HAYIR. Su an sadece preview/audit dosyalari uretildi. Master'lara veya Production DB'ye dokunulmadi.

E) Sonraki adim icin onay gerekiyor mu?
-> EVET. "Safe to apply" olan distillery zenginlestirmelerinin master'a (veya ayri bir db guncelleme aracina) gonderilmesi ve Knowledge table import'larinin (regions, glossary, guides) uygulanmasi icin patch onayi beklenmektedir.
"""
with open("29_whiskeyfyi_final_decision_gate.txt", "w", encoding="utf-8") as f:
    f.write(gate_29)
