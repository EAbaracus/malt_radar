import logging

logger = logging.getLogger(__name__)

def extract_from_database_row(row: dict) -> dict:
    """
    Deterministically extracts canonical fields from a Database Dump row (CSV).
    Does NOT hallucinate, guess, or synthesize missing data.
    """
    extracted = {}

    def add_field(field_name: str, csv_column: str, parser=str):
        raw_val = row.get(csv_column)
        if raw_val and raw_val.strip():
            try:
                parsed_val = parser(raw_val.strip())
                extracted[field_name] = {
                    "value": parsed_val,
                    "quote": f"[{csv_column}] {raw_val}",
                    "confidence": 1.0  # Structural extraction is fully confident
                }
            except ValueError:
                logger.warning(f"Could not parse {raw_val} for {field_name}")

    add_field("distillery_name", "distillery")
    add_field("region", "region")
    add_field("country", "country")
    add_field("cask_type", "cask_type_primary")
    add_field("abv", "approx_abv", float)
    add_field("age_statement", "age_statement_years", int)

    # Note: nose, palate, finish, flavor_axes are NOT present in candidate_list.csv.
    # Therefore, we leave them completely omitted.
    
    return extracted

def run_extraction(document_data: dict, document_type: str) -> dict:
    """
    Main extraction interface. 
    In P76, our 'document' is a row from the CSV Database Dump.
    """
    if document_type == "Database Dump":
        return extract_from_database_row(document_data)
    else:
        # Fallback for unrecognized classes, returns empty
        return {}
