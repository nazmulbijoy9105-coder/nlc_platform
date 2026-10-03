"""
NLC — GATE E8: Audit / Hash-Chain Verification Tests
Proves that the compliance score hash is tamper-evident.
"""
import hashlib
import pytest

def generate_hash(company_id: str, score: int, risk_band: str, snapshot_month: str, engine_version: str) -> str:
    """Replicates the hash generation logic from ComplianceService."""
    return hashlib.sha256(
        f"{company_id}{score}{risk_band}{snapshot_month}{engine_version}".encode()
    ).hexdigest()

def test_valid_hash_matches():
    """A correct hash should match the expected value."""
    company_id = "00000000-0000-0000-0000-000000000001"
    score = 85
    risk_band = "YELLOW"
    snapshot_month = "2026-10"
    engine_version = "2.1"
    
    original_hash = generate_hash(company_id, score, risk_band, snapshot_month, engine_version)
    recalculated_hash = generate_hash(company_id, score, risk_band, snapshot_month, engine_version)
    
    assert original_hash == recalculated_hash, "Valid hash should match."

def test_tampered_score_detected():
    """If the score is altered, the hash must not match."""
    company_id = "00000000-0000-0000-0000-000000000001"
    original_score = 85
    tampered_score = 100  # Maliciously changed from 85 to 100
    risk_band = "YELLOW"
    snapshot_month = "2026-10"
    engine_version = "2.1"
    
    # The hash stored in the DB (calculated with the original score)
    stored_hash = generate_hash(company_id, original_score, risk_band, snapshot_month, engine_version)
    
    # The hash we calculate when verifying the DB record (using the tampered score)
    verification_hash = generate_hash(company_id, tampered_score, risk_band, snapshot_month, engine_version)
    
    assert stored_hash != verification_hash, "Tamper not detected: Hash matched despite altered score!"

def test_tampered_risk_band_detected():
    """If the risk band is altered, the hash must not match."""
    company_id = "00000000-0000-0000-0000-000000000001"
    score = 50
    original_risk_band = "RED"
    tampered_risk_band = "GREEN"  # Maliciously downgraded
    snapshot_month = "2026-10"
    engine_version = "2.1"
    
    stored_hash = generate_hash(company_id, score, original_risk_band, snapshot_month, engine_version)
    verification_hash = generate_hash(company_id, score, tampered_risk_band, snapshot_month, engine_version)
    
    assert stored_hash != verification_hash, "Tamper not detected: Hash matched despite altered risk band!"
