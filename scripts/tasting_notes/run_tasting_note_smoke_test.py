import os
import sys
import logging

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from scripts.tasting_notes.masterofmalt_adapter import MasterOfMaltAdapter
from scripts.tasting_notes.whiskynotes_adapter import WhiskyNotesAdapter
from scripts.tasting_notes.whiskyedition_adapter import WhiskyEditionAdapter
from scripts.tasting_notes.whiskybase_adapter import WhiskybaseAdapter
from scripts.tasting_notes.thewhiskyexchange_flavour_adapter import TheWhiskyExchangeFlavourAdapter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    urls = [
        ("MasterOfMalt", "https://www.masterofmalt.com/whiskies/arran/arran-10-year-old-whisky/?sku=1743", MasterOfMaltAdapter()),
        ("WhiskyNotes", "https://www.whiskynotes.be/2024/glenfarclas/glenfarclas-8-year-old/", WhiskyNotesAdapter()),
        ("WhiskyEdition", "https://thewhiskyedition.com/whisky-reviews/dalmore-2007-2017-10-years-a-d-rattray", WhiskyEditionAdapter()),
        ("Whiskybase", "https://www.whiskybase.com/whiskies/whisky/246529/ardbeg-ten", WhiskybaseAdapter()),
        ("TheWhiskyExchange", "https://www.thewhiskyexchange.com/feature/whiskybyflavour", TheWhiskyExchangeFlavourAdapter())
    ]
    
    successes = 0
    results = []
    
    for name, url, adapter in urls:
        try:
            logging.info(f"Running {name}...")
            result = adapter.run(url)
            if result == 'SUCCESS':
                successes += 1
                results.append(f"- {name}: SUCCESS")
            elif result == 'PARSE_EMPTY':
                results.append(f"- {name}: PARSE_EMPTY")
            elif result == 'DUPLICATE':
                results.append(f"- {name}: DUPLICATE")
            else:
                results.append(f"- {name}: FAILED ({result})")
        except Exception as e:
            results.append(f"- {name}: ERROR ({e})")
            logging.error(f"Adapter {name} crashed: {e}")
            
    # Generate Smoke Report
    os.makedirs('output/reports', exist_ok=True)
    report_path = 'output/reports/176_tasting_note_scraper_smoke_report.md'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Tasting Note Scraper Smoke Report\n\n")
        f.write("## Adapter Results\n")
        f.write("\n".join(results) + "\n\n")
        f.write(f"Total Successes: {successes} / {len(urls)}\n")
        
    gate_path = 'output/reports/178_tasting_note_scraper_go_no_go_gate.txt'
    if successes >= 3:
        with open(gate_path, 'w', encoding='utf-8') as f:
            f.write("GO")
        logging.info("Smoke test passed (>= 3 successes). Written GO to gate file.")
    else:
        with open(gate_path, 'w', encoding='utf-8') as f:
            f.write("NO-GO")
        logging.error("Smoke test failed (< 3 successes). Written NO-GO to gate file.")

if __name__ == '__main__':
    main()
