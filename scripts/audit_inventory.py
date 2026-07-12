import os
import hashlib
import csv
import json
import pypdf
from pathlib import Path

# Paths
REPO_ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
NEW_DATA_DIR = REPO_ROOT / "data" / "books" / "yeni veriler"
EXISTING_DATA_DIR = REPO_ROOT / "data" / "books"
OUTPUT_DIR = REPO_ROOT / "output" / "reports"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_pdf_info(file_path):
    try:
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            total_pages = len(reader.pages)
            scanned_pages = 0
            
            for page in reader.pages:
                text = page.extract_text()
                if not text or len(text.strip()) < 50:
                    scanned_pages += 1
            
            scanned_ratio = scanned_pages / total_pages if total_pages > 0 else 0
            has_text_layer = scanned_ratio < 1.0
            ocr_required = scanned_ratio > 0.1
            
            return {
                "pages": total_pages,
                "has_text_layer": "Yes" if has_text_layer else "No",
                "scanned_ratio": round(scanned_ratio, 4),
                "ocr_required": "Yes" if ocr_required else "No"
            }
    except Exception as e:
        return {
            "pages": "Error",
            "has_text_layer": "Error",
            "scanned_ratio": "Error",
            "ocr_required": "Error",
            "error_msg": str(e)
        }

def classify_file(file_name):
    name_lower = file_name.lower()
    if "catalogue" in name_lower or "catalog" in name_lower or "product" in name_lower:
        return "catalog/product_list"
    elif "brand" in name_lower:
        return "catalog/product_list"
    elif "distillery" in name_lower or "distilleries" in name_lower:
        return "whisky_reference_book"
    elif "tasting" in name_lower or "review" in name_lower:
        return "tasting_notes_source"
    elif "flavor" in name_lower or "flavour" in name_lower or "profile" in name_lower:
        return "flavor_profile_source"
    elif any(x in name_lower for x in ["bible", "guide", "atlas", "encyclopedia", "book"]):
        return "whisky_reference_book"
    else:
        return "unknown"

def build_existing_inventory():
    existing_files = {}
    # Scan existing files in data/books, excluding 'yeni veriler' directory
    for root, dirs, files in os.walk(EXISTING_DATA_DIR):
        if "yeni veriler" in Path(root).parts:
            continue
        for file in files:
            path = Path(root) / file
            if file.lower() in [".gitignore", "test_book.txt"]:
                continue
            try:
                sha256 = calculate_sha256(path)
                existing_files[sha256] = {
                    "name": file,
                    "path": str(path.relative_to(REPO_ROOT)),
                    "size": path.stat().st_size
                }
            except Exception as e:
                print(f"Error hashing existing file {path}: {e}")
    return existing_files

def main():
    print("Building inventory of existing files for duplicate check...")
    existing_db = build_existing_inventory()
    print(f"Indexed {len(existing_db)} existing files.")

    print("\nScanning new data directory...")
    new_files_inventory = []
    
    if not NEW_DATA_DIR.exists():
        print(f"Error: Directory {NEW_DATA_DIR} does not exist!")
        return

    for root, dirs, files in os.walk(NEW_DATA_DIR):
        for file in files:
            path = Path(root) / file
            ext = path.suffix.lower()
            size = path.stat().st_size
            sha256 = calculate_sha256(path)
            
            # PDF checks
            pdf_info = None
            if ext == ".pdf":
                pdf_info = get_pdf_info(path)
            
            # Duplicate check
            duplicate_found = sha256 in existing_db
            duplicate_with = existing_db[sha256]["path"] if duplicate_found else "None"
            
            # Near duplicate check by name/size
            near_duplicate = "None"
            if not duplicate_found:
                for ex_sha, ex_info in existing_db.items():
                    if ex_info["name"].lower() == file.lower() or (abs(ex_info["size"] - size) < 100 and ex_info["name"].lower() == file.lower()):
                        near_duplicate = f"{ex_info['path']} (Size diff: {ex_info['size'] - size} bytes)"
                        break

            classification = classify_file(file)
            
            row = {
                "file_name": file,
                "extension": ext,
                "size_bytes": size,
                "size_kb": round(size / 1024, 2),
                "sha256": sha256,
                "pdf_pages": pdf_info["pages"] if pdf_info else "N/A",
                "has_text_layer": pdf_info["has_text_layer"] if pdf_info else "N/A",
                "scanned_ratio": pdf_info["scanned_ratio"] if pdf_info else "N/A",
                "ocr_required": pdf_info["ocr_required"] if pdf_info else "N/A",
                "is_duplicate": "Yes" if duplicate_found else "No",
                "duplicate_of": duplicate_with,
                "near_duplicate_of": near_duplicate,
                "classification": classification
            }
            new_files_inventory.append(row)

    # Save to CSV
    csv_file = OUTPUT_DIR / "books_new_inventory.csv"
    headers = [
        "file_name", "extension", "size_bytes", "size_kb", "sha256", 
        "pdf_pages", "has_text_layer", "scanned_ratio", "ocr_required", 
        "is_duplicate", "duplicate_of", "near_duplicate_of", "classification"
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(new_files_inventory)
    print(f"Saved CSV report to {csv_file}")

    # Generate MD Report
    md_file = OUTPUT_DIR / "books_new_inventory.md"
    generate_md_report(new_files_inventory, md_file)
    print(f"Saved Markdown report to {md_file}")

def generate_md_report(inventory, output_path):
    total_files = len(inventory)
    file_types = {}
    duplicate_count = 0
    near_duplicate_count = 0
    ocr_required_count = 0
    classifications = {}
    
    for item in inventory:
        ext = item["extension"]
        file_types[ext] = file_types.get(ext, 0) + 1
        
        if item["is_duplicate"] == "Yes":
            duplicate_count += 1
        if item["near_duplicate_of"] != "None":
            near_duplicate_count += 1
        if item["ocr_required"] == "Yes":
            ocr_required_count += 1
            
        cls = item["classification"]
        classifications[cls] = classifications.get(cls, 0) + 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Malt Radar - Yeni Kitap Verisi Envanter ve Denetim Raporu\n\n")
        f.write(f"**Oluşturulma Tarihi:** 2026-07-12\n")
        f.write(f"**Tarama Yolu:** `data/books/yeni veriler`\n\n")
        
        f.write("## 1. Genel Özet\n")
        f.write(f"- **Toplam Dosya Sayısı:** {total_files}\n")
        f.write("- **Dosya Tipleri Dağılımı:**\n")
        for ext, count in file_types.items():
            f.write(f"  - `{ext}`: {count} adet\n")
        f.write(f"- **Birebir Kopya (Duplicate) Sayısı:** {duplicate_count}\n")
        f.write(f"- **Benzer İsim/Boyut (Near-Duplicate) Sayısı:** {near_duplicate_count}\n")
        f.write(f"- **OCR Gerektiren PDF Sayısı:** {ocr_required_count}\n\n")

        f.write("## 2. Sınıflandırma ve Pipeline Uygunluğu\n")
        f.write("| Sınıflandırma | Dosya Sayısı | Uygun Pipeline | Açıklama |\n")
        f.write("| --- | --- | --- | --- |\n")
        
        pipeline_mapping = {
            "whisky_reference_book": "Reference Book Ingestion / Entity Linkage",
            "tasting_notes_source": "Tasting Notes Extraction Pipeline",
            "flavor_profile_source": "Flavor Profile Vector Generation",
            "catalog/product_list": "Product Matching & Catalog Enrichment",
            "unknown": "Triage / Manual Ingestion"
        }
        
        for cls, count in classifications.items():
            pipeline = pipeline_mapping.get(cls, "Triage")
            desc = ""
            if cls == "catalog/product_list":
                desc = "Marka, viski isimleri, hacim ve puan bilgilerini içerir. Ürün eşleştirme için uygundur."
            elif cls == "whisky_reference_book":
                desc = "Damıtımevi, üretim lokasyonu, kurucular ve kapasite bilgisi içerir."
            elif cls == "tasting_notes_source":
                desc = "Tadım notları ve duyusal değerlendirmeler içerir."
            elif cls == "flavor_profile_source":
                desc = "Aroma profilleri ve lezzet yoğunluğu vektörleri içerir."
            f.write(f"| `{cls}` | {count} | {pipeline} | {desc} |\n")
        f.write("\n")

        f.write("## 3. Detaylı Dosya Envanteri\n")
        f.write("| Dosya Adı | Boyut (KB) | Sınıflandırma | Duplicate? | PDF Sayfa | OCR Gereksinimi? |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for item in inventory:
            dup_status = "Evet" if item["is_duplicate"] == "Yes" else "Hayır"
            if item["near_duplicate_of"] != "None":
                dup_status += " (Benzer)"
            f.write(f"| {item['file_name']} | {item['size_kb']} | `{item['classification']}` | {dup_status} | {item['pdf_pages']} | {item['ocr_required']} |\n")
        f.write("\n")

        f.write("## 4. Çakışma ve Yinelenen Veri Analizi\n")
        has_dups = False
        for item in inventory:
            if item["is_duplicate"] == "Yes" or item["near_duplicate_of"] != "None":
                has_dups = True
                f.write(f"### Dosya: {item['file_name']}\n")
                f.write(f"- **SHA256 Hash:** `{item['sha256']}`\n")
                if item["is_duplicate"] == "Yes":
                    f.write(f"- **Birebir Kopya:** Var olan dosya: `{item['duplicate_of']}`\n")
                if item["near_duplicate_of"] != "None":
                    f.write(f"- **Benzer Dosya:** `{item['near_duplicate_of']}`\n")
                f.write("\n")
        if not has_dups:
            f.write("Herhangi bir yinelenen dosya (birebir kopya veya benzer) bulunamadı.\n\n")

        f.write("## 5. Tahmini Veri Kazanımı (Estimated Data Yield)\n")
        f.write("Dosya içeriklerine göre tahmin edilen veri kazanımı şu şekildedir:\n\n")
        for item in inventory:
            name = item["file_name"]
            cls = item["classification"]
            f.write(f"### {name} (`{cls}`)\n")
            if name == "distilleries.csv":
                f.write("- **İçerik:** Damıtımevleri verileri (351 satır)\n")
                f.write("- **Kazanım:** Üretici ve damıtımevi tablosunu (`distilleries`) kurucu, konum, bölge, kuruluş tarihi ve kapasite bazında güncelleme/zenginleştirme.\n")
            elif name == "brands.csv":
                f.write("- **İçerik:** Markalar verileri (263 satır)\n")
                f.write("- **Kazanım:** Sahip (owner), damıtımevi ve ülke ilişkilerini zenginleştirme, yeni marka alias'ları çıkarma.\n")
            elif name == "catalogue.csv":
                f.write("- **İçerik:** Viski Kataloğu verileri (374 satır)\n")
                f.write("- **Kazanım:** Viski ürünleri (`whisky_products`) için ortalama rating değerleri ve görsel URL enrichment, eşleşmeyen yeni ürünlerin manual review kuyruğuna alınması.\n")
            else:
                f.write("- İçerik analizine göre belirlenecektir.\n")
            f.write("\n")

        f.write("## 6. Malt Radar Veri Kuralları Hatırlatması\n")
        f.write("- **Tadım Profilleri:** Aynı ürünün farklı batch'leri arasında duyusal bir fark kanıtlanmadıkça ayrı profil açılmamalıdır.\n")
        f.write("- **İzlenebilirlik:** Kaynak kitap ve sayfa bilgileri metadata olarak tutulmalıdır.\n")
        f.write("- **Güvenlik & Lisans:** Kaynak kitap metinleri kesinlikle public arayüze (UI) sızdırılmamalı, sadece internal eşleştirme ve arama için indekslenmelidir.\n")
        f.write("- **Doğrulama:** Otomatik eşleşen tüm kayıtlar doğrudan yayına alınmamalı, `staging/manual review` kuyruğuna aktarılmalıdır.\n")

if __name__ == "__main__":
    main()
