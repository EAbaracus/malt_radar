# Knowledge Tables Integration Plan

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
