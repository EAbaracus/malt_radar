import os
import csv

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
output_dir = os.path.join(base_dir, "data", "output")
reports_dir = os.path.join(base_dir, "output", "reports")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)

csv_path = os.path.join(output_dir, "real_tasting_note_acquisition_strategy_matrix.csv")
report_path = os.path.join(reports_dir, "295_real_tasting_note_acquisition_strategy_report.md")
gate_path = os.path.join(reports_dir, "296_12x_real_tasting_note_acquisition_strategy_gate.txt")

strategies = [
    {
        "strategy": "Manual curated URL/file import",
        "feasibility": "High",
        "legal_risk": "Low (requires fair use review of sources)",
        "data_quality_risk": "Low (human vetted)",
        "engineering_effort": "Low (pipeline already exists for uploaded_document/manual CSV)",
        "expected_yield": "Low-Medium (time intensive)",
        "cost": "Free",
        "recommendation": "Recommended as baseline",
        "next_phase": "Prepare template CSV for manual note collection"
    },
    {
        "strategy": "Playwright/Selenium browser fetch",
        "feasibility": "Medium",
        "legal_risk": "Medium (must respect robots.txt and Terms of Service)",
        "data_quality_risk": "Medium (requires DOM parsing per site)",
        "engineering_effort": "High",
        "expected_yield": "Medium-High",
        "cost": "Free",
        "recommendation": "Not recommended (high maintenance, potential ToS violations)",
        "next_phase": "N/A"
    },
    {
        "strategy": "Scraping API services (ScrapingBee, ZenRows)",
        "feasibility": "High",
        "legal_risk": "Medium (outsources fetch but underlying legal/ToS risks persist)",
        "data_quality_risk": "Medium",
        "engineering_effort": "Medium",
        "expected_yield": "High",
        "cost": "Paid ($$)",
        "recommendation": "Not recommended (costly, anti-bot bypass is discouraged)",
        "next_phase": "N/A"
    },
    {
        "strategy": "Source Exchange (API / RSS / Sitemap / Static HTML)",
        "feasibility": "Medium",
        "legal_risk": "Low (using publicly provided developer endpoints or feeds)",
        "data_quality_risk": "Low",
        "engineering_effort": "Medium",
        "expected_yield": "Medium",
        "cost": "Free / Freemium",
        "recommendation": "Highly Recommended for automation",
        "next_phase": "Identify whisky DB APIs or official RSS feeds"
    },
    {
        "strategy": "In-app User-generated Tasting Notes",
        "feasibility": "High",
        "legal_risk": "None",
        "data_quality_risk": "Medium-High (requires moderation/aggregation)",
        "engineering_effort": "Medium (frontend/backend feature)",
        "expected_yield": "High (long-term, scales with user base)",
        "cost": "Free",
        "recommendation": "Highly Recommended as long-term core strategy",
        "next_phase": "Design UGC schema for tasting notes"
    },
    {
        "strategy": "Disable Current Web Pipeline",
        "feasibility": "High",
        "legal_risk": "None",
        "data_quality_risk": "None",
        "engineering_effort": "Low",
        "expected_yield": "Zero",
        "cost": "Free",
        "recommendation": "Mandatory immediately",
        "next_phase": "Archive discovery/fetch scripts and freeze automated pipeline"
    }
]

def main():
    # 1. Write CSV
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        fields = list(strategies[0].keys())
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(strategies)

    # 2. Write Markdown Report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 295 Real Tasting Note Acquisition Strategy Report\n\n")
        f.write("""\nEstimated API Cost: $0.00\nActual API Cost: $0.00\nLocal Compute Used: Yes\nFully Local Execution: Yes\n""")

        f.write("## Evaluated Strategies\n\n")
        for s in strategies:
            f.write(f"### {s['strategy']}\n")
            for k, v in s.items():
                if k != "strategy":
                    f.write(f"- **{k}**: {v}\n")
            f.write("\n")
        
        f.write("## Recommendation & Next Steps\n")
        f.write("The current automated scraping pipeline is hitting anti-bot walls. Circumventing these is discouraged. ")
        f.write("The recommended approach is a hybrid of: **Manual curated file import** (for high quality baseline) ")
        f.write("and **In-app User-generated Notes** (for scalable organic growth). The current scraping pipeline should be paused.\n\n")
        f.write("- production_db_changed: NO\n")
        f.write("- output_import_changed: NO\n")

    # 3. Write Gate
    with open(gate_path, "w", encoding="utf-8") as f:
        f.write("GATE: GO\n")
        f.write("REASON: Evaluated 6 acquisition strategies.\n")
        f.write("REASON: Recommended ethical/sustainable solutions over anti-bot bypass.\n")
        f.write("REASON: production.db and output/import untouched.\n")

if __name__ == "__main__":
    main()
