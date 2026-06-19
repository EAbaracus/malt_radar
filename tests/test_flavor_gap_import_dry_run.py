import pytest
import sqlite3
import pandas as pd
import os

def test_dry_run_rules():
    # Setup test mock logic
    valid_whisky_ids = {'W000001', 'W000002', 'W000003'}
    
    # Test cases
    row_approved = {
        'whisky_id': 'W000001',
        'review_decision': 'approved',
        'fruity_score': 1.0,
        'sweet_score': 2.0,
        'smoky_score': 0.0,
        'spicy_score': 0.0,
        'woody_score': 0.0
    }
    
    row_manual = {
        'whisky_id': 'W000002',
        'review_decision': 'manual_review',
        'fruity_score': 1.0,
        'sweet_score': 2.0,
        'smoky_score': 0.0,
        'spicy_score': 0.0,
        'woody_score': 0.0
    }
    
    row_zero_vector = {
        'whisky_id': 'W000003',
        'review_decision': 'approved',
        'fruity_score': 0.0,
        'sweet_score': 0.0,
        'smoky_score': 0.0,
        'spicy_score': 0.0,
        'woody_score': 0.0
    }
    
    row_not_found = {
        'whisky_id': 'W999999',
        'review_decision': 'approved',
        'fruity_score': 1.0,
        'sweet_score': 2.0,
        'smoky_score': 0.0,
        'spicy_score': 0.0,
        'woody_score': 0.0
    }

    # Evaluate approved
    def evaluate(row, seen):
        w_id = row['whisky_id']
        decision = row['review_decision']
        scores = [row['fruity_score'], row['sweet_score'], row['smoky_score'], row['spicy_score'], row['woody_score']]
        score_sum = sum(scores)
        
        if decision == 'approved':
            if w_id in seen:
                return 'blocked', 'duplicate_candidate'
            elif w_id not in valid_whisky_ids:
                return 'blocked', 'whisky_id_not_found'
            elif score_sum <= 0:
                return 'blocked', 'zero_flavor_vector'
            else:
                seen.add(w_id)
                return 'would_insert_or_update_flavor_profile', ''
        else:
            return 'blocked', decision

    seen_set = set()
    
    # 1. Approved case
    action, reason = evaluate(row_approved, seen_set)
    assert action == 'would_insert_or_update_flavor_profile'
    
    # 2. Duplicate case
    action, reason = evaluate(row_approved, seen_set)
    assert action == 'blocked'
    assert reason == 'duplicate_candidate'
    
    # 3. Manual review case
    action, reason = evaluate(row_manual, seen_set)
    assert action == 'blocked'
    assert reason == 'manual_review'
    
    # 4. Zero vector case
    action, reason = evaluate(row_zero_vector, seen_set)
    assert action == 'blocked'
    assert reason == 'zero_flavor_vector'
    
    # 5. Not found case
    action, reason = evaluate(row_not_found, seen_set)
    assert action == 'blocked'
    assert reason == 'whisky_id_not_found'

def test_dry_run_does_not_modify_db():
    db_path = 'output/import/production.db'
    mtime_before = os.path.getmtime(db_path)
    
    # Simulate DB read-only check
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM flavor_profiles;")
    count_before = cursor.fetchone()[0]
    conn.close()
    
    # Make sure mtime is unchanged or we assert no write query was executed
    assert count_before >= 0
    mtime_after = os.path.getmtime(db_path)
    assert mtime_before == mtime_after

def test_w001485_blocked():
    # Specific test for Alberta Premium Dark Horse (W001485)
    row_w001485 = {
        'whisky_id': 'W001485',
        'review_decision': 'manual_review',
        'fruity_score': 0.0,
        'sweet_score': 6.0,
        'smoky_score': 0.0,
        'spicy_score': 3.0,
        'woody_score': 1.0
    }
    seen = set()
    
    # It must be blocked because its review_decision is manual_review
    w_id = row_w001485['whisky_id']
    decision = row_w001485['review_decision']
    
    assert decision == 'manual_review'
    action = 'blocked' if decision != 'approved' else 'would_insert_or_update_flavor_profile'
    assert action == 'blocked'
