# ROI Ingestion Ranking

Ingestion candidates ranked by ROI:

$$ROI = Coverage \, Gain \times Metadata \, Importance \times Reliability \times Automation \, Cost$$

| Rank | Asset Name | Target Fields | Reliability | Automation Cost | ROI Class |
|---|---|---|---|---|---|
| **1** | **SMWS Staging Datasets** | Cask Type, Tasting Notes, ABV | High | Low (Pre-staged) | **IMMEDIATE** |
| **2** | **Malt Whisky Yearbook 2019** | Distillery metadata, Regions | High | Low (Highly structured) | **HIGH** |
| **3** | **World Atlas of Whisky** | ABV, Age, Region, Tasting Notes | High | Medium (Text parser) | **HIGH** |
| **4** | **Whisky Classified (Wishart)** | Flavour Profiles | High | Low (Structured) | **HIGH** |
| **5** | **Jim Murray's Whisky Bible** | Tasting Notes, ABV, Ratings | Medium | High (Stylized OCR) | **MEDIUM** |
