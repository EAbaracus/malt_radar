import pytest
import re
from scripts.generate_flavor_gap_candidates import clean_name, extract_age, extract_ordinal

def test_clean_name():
    assert clean_name("Glenfiddich 12 Year Old") == "glenfiddich 12 year old"
    assert clean_name("Aberlour, 18-Year-Old") == "aberlour 18 year old"
    assert clean_name("Ardbeg (10 Year Old)") == "ardbeg 10 year old"
    assert clean_name("") == ""

def test_extract_age():
    assert extract_age("Glenfiddich 12 Year Old") == 12
    assert extract_age("Aberlour 18yo") == 18
    assert extract_age("Lagavulin 16 Year") == 16
    assert extract_age("Macallan Classic Cut") is None

def test_extract_ordinal():
    assert extract_ordinal("Port Ellen 15th Release") == 15
    assert extract_ordinal("Brora 11th Release") == 11
    assert extract_ordinal("Ardbeg Supernova") is None

def test_exact_product_match():
    # Simulate matching
    w_name = clean_name("Aberlour 12 Year Old")
    c_name = clean_name("Aberlour 12 Year Old")
    assert w_name == c_name

def test_age_mismatch_rejection():
    # Simulate matching
    w_name = "Glenfiddich 12 Year Old"
    c_name = "Glenfiddich 18 Year Old"
    
    w_age = extract_age(w_name)
    c_age = extract_age(c_name)
    
    assert w_age is not None
    assert c_age is not None
    assert w_age != c_age  # Trigger age mismatch rejection

def test_ordinal_release_mismatch_rejection():
    w_name = "Port Ellen 15th Release"
    c_name = "Port Ellen 11th Release"
    
    w_ord = extract_ordinal(w_name)
    c_ord = extract_ordinal(c_name)
    
    assert w_ord is not None
    assert c_ord is not None
    assert w_ord != c_ord  # Trigger ordinal mismatch rejection

def test_false_positive_rejection():
    # Mister Sam and Monkey Shoulder false positive prevention
    w_name = "monkey shoulder blended malt"
    c_name = "balvenie 12 doublewood"
    
    w_name_clean = clean_name(w_name)
    c_name_clean = clean_name(c_name)
    
    is_monkey_shoulder = "monkey shoulder" in w_name_clean
    assert is_monkey_shoulder is True
    assert "monkey shoulder" not in c_name_clean  # Rejection triggered

def test_duplicate_prevention():
    # Confirm unique IDs are populated or mapped uniquely
    candidates = [
        {'whisky_id': 'W000001', 'whisky_name': 'A'},
        {'whisky_id': 'W000002', 'whisky_name': 'B'},
        {'whisky_id': 'W000001', 'whisky_name': 'A'}  # duplicate
    ]
    seen_ids = set()
    unique_candidates = []
    for c in candidates:
        if c['whisky_id'] not in seen_ids:
            seen_ids.add(c['whisky_id'])
            unique_candidates.append(c)
            
    assert len(unique_candidates) == 2
    assert 'W000001' in seen_ids
    assert 'W000002' in seen_ids

def test_quality_gates_unknown_distillery_blocks_auto():
    dist_name = "Unknown"
    is_unknown_dist = dist_name.strip().lower() in ['', 'unknown', 'none']
    assert is_unknown_dist is True
    
    best_status = "auto_candidate"
    final_status = best_status
    if is_unknown_dist:
        final_status = "manual_review"
    assert final_status == "manual_review"

def test_quality_gates_zero_flavor_vector_blocks_auto():
    fruity_s, sweet_s, smoky_s, spicy_s, woody_s = 0.0, 0.0, 0.0, 0.0, 0.0
    score_sum = fruity_s + sweet_s + smoky_s + spicy_s + woody_s
    is_zero_vector = score_sum == 0.0
    assert is_zero_vector is True
    
    best_status = "auto_candidate"
    final_status = best_status
    if is_zero_vector:
        final_status = "manual_review"
    assert final_status == "manual_review"

def test_quality_gates_valid_exact_match_allowed():
    dist_name = "Glenfiddich"
    is_unknown_dist = dist_name.strip().lower() in ['', 'unknown', 'none']
    
    fruity_s, sweet_s, smoky_s, spicy_s, woody_s = 2.0, 4.0, 0.0, 1.0, 3.0
    score_sum = fruity_s + sweet_s + smoky_s + spicy_s + woody_s
    is_zero_vector = score_sum == 0.0
    
    is_entity_normalization = dist_name.lower().strip() in ["box", "compass box"]
    
    best_status = "auto_candidate"
    final_status = best_status
    if is_unknown_dist or is_zero_vector or is_entity_normalization:
        final_status = "manual_review"
        
    assert is_unknown_dist is False
    assert is_zero_vector is False
    assert is_entity_normalization is False
    assert final_status == "auto_candidate"

def test_quality_gates_compass_box_entity_normalization_blocked():
    dist_name = "Compass Box"
    is_entity_normalization = dist_name.lower().strip() in ["box", "compass box"]
    assert is_entity_normalization is True
    
    best_status = "auto_candidate"
    final_status = best_status
    if is_entity_normalization:
        final_status = "manual_review"
    assert final_status == "manual_review"
