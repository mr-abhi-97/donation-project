import io
import sys
import os
import json
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import pandas as pd
import numpy as np
from PIL import Image, ImageDraw

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.anti_fraud_service import ScreenshotFraudDetector
from backend.app.services.statement_verifier import StatementAuditor
from backend.app.utils.validators import normalize_indian_phone, validate_pan_format
from backend.app.services.notification_service import NotificationService

def test_module_1_anti_fraud():
    print("\n--- Testing Module 1: Anti-Fraud & Media Inspection Engine ---")
    
    # 1. SHA-256 Hash
    test_bytes = b"RaiseIndiaFoundationFakeScreenshot123456"
    file_hash = ScreenshotFraudDetector.calculate_file_hash(test_bytes)
    assert len(file_hash) == 64, "SHA-256 must be 64 hex characters"
    print(f"✓ calculate_file_hash SHA-256 verified: {file_hash[:16]}...")

    # 2. ELA (Error Level Analysis)
    # Create clean image
    img = Image.new("RGB", (200, 100), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), "Original Text UPI 5000", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    clean_bytes = buf.getvalue()

    ela_result = ScreenshotFraudDetector.run_error_level_analysis(clean_bytes, quality=90)
    assert "tamper_score" in ela_result
    assert "is_tampered" in ela_result
    assert "ela_base64" in ela_result
    print(f"✓ run_error_level_analysis clean image: tamper_score={ela_result['tamper_score']:.2f}, is_tampered={ela_result['is_tampered']}")

    # 3. UTR Syntax & Julian Date Validation
    # Valid: 4 (year 2024), 289 (day 289), 1029381 (unique seq) -> 12 digits
    valid_utr = "428910293812"
    res_valid = ScreenshotFraudDetector.validate_utr_syntax(valid_utr)
    assert res_valid["is_valid"] is True, f"Expected valid UTR, got: {res_valid}"
    print(f"✓ validate_utr_syntax on legitimate UTR '{valid_utr}': Valid")

    # Invalid: dummy sequences
    for dummy in ["000000000000", "111111111111", "123456789012"]:
        res_dummy = ScreenshotFraudDetector.validate_utr_syntax(dummy)
        assert res_dummy["is_valid"] is False
        print(f"✓ validate_utr_syntax correctly rejected dummy '{dummy}': {res_dummy['rejection_reason']}")

    # Invalid: Julian day out of range (day 400 doesn't exist)
    res_julian = ScreenshotFraudDetector.validate_utr_syntax("440010293812")
    assert res_julian["is_valid"] is False
    print(f"✓ validate_utr_syntax correctly rejected invalid Julian day: {res_julian['rejection_reason']}")

    # Invalid: length != 12
    assert ScreenshotFraudDetector.validate_utr_syntax("12345")["is_valid"] is False
    print("✓ validate_utr_syntax correctly rejected non-12-digit UTR")


def test_module_2_statement_verifier():
    print("\n--- Testing Module 2: Bank Statement Mathematical & Metadata Audit ---")
    
    # 1. Running balance math audit
    # Valid dataframe: Bal(N) = Bal(N-1) + Dep - Wdl
    df_valid = pd.DataFrame([
        {"Date": "2024-10-01", "Narration": "Opening", "Deposit": 1000.0, "Withdrawal": 0.0, "Balance": 1000.0},
        {"Date": "2024-10-02", "Narration": "Donation 1", "Deposit": 5000.0, "Withdrawal": 0.0, "Balance": 6000.0},
        {"Date": "2024-10-03", "Narration": "Vendor Exp", "Deposit": 0.0, "Withdrawal": 2000.0, "Balance": 4000.0},
    ])
    audit_valid = StatementAuditor.audit_running_balance(df_valid)
    assert audit_valid["is_math_valid"] is True
    assert audit_valid["total_discrepancies"] == 0
    print(f"✓ audit_running_balance on continuous statement: is_math_valid={audit_valid['is_math_valid']}, discrepancies={audit_valid['total_discrepancies']}")

    # Broken dataframe: rogue inserted row
    df_broken = pd.DataFrame([
        {"Date": "2024-10-01", "Narration": "Opening", "Deposit": 1000.0, "Withdrawal": 0.0, "Balance": 1000.0},
        {"Date": "2024-10-02", "Narration": "Fake Row", "Deposit": 5000.0, "Withdrawal": 0.0, "Balance": 9999.0}, # Wrong balance!
    ])
    audit_broken = StatementAuditor.audit_running_balance(df_broken)
    assert audit_broken["is_math_valid"] is False
    assert audit_broken["total_discrepancies"] == 1
    assert len(audit_broken["broken_rows"]) == 1
    print(f"✓ audit_running_balance caught broken row: expected={audit_broken['broken_rows'][0]['expected_balance']}, stated={audit_broken['broken_rows'][0]['stated_balance']}")


def test_module_3_validators_and_whatsapp():
    print("\n--- Testing Module 3: Phone Normalization & WhatsApp Notification ---")
    
    # 1. Phone Normalization (E.164 standard)
    test_phones = [
        ("9876543210", "+919876543210"),
        ("09876543210", "+919876543210"),
        ("919876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("91-98765-43210", "+919876543210"),
    ]
    for inp, expected in test_phones:
        out = normalize_indian_phone(inp)
        assert out == expected, f"Failed for {inp}: expected {expected}, got {out}"
    print(f"✓ normalize_indian_phone correctly normalized all formats to E.164: +919876543210")

    # Invalid phone prefixes
    try:
        normalize_indian_phone("5123456789") # Prefix 5 is invalid in India
        assert False, "Should raise ValueError for invalid prefix"
    except ValueError as e:
        print(f"✓ normalize_indian_phone caught invalid telecom prefix (5): {e}")

    # 2. WhatsApp Meta Cloud API Payload formatting
    import asyncio
    async def run_whatsapp_test():
        res = await NotificationService.send_whatsapp_80g_receipt(
            phone="+919876543210",
            donor_name="Dr. Anita Desai",
            receipt_url="http://localhost:8000/api/receipts/download/rec1",
            amount=5000.0
        )
        assert res["status"] == "DISPATCHED"
        payload = res["payload"]
        assert payload["template"]["name"] == "receipt_80g_issued"
        assert payload["to"] == "919876543210"
        components = payload["template"]["components"]
        body_comp = next(c for c in components if c["type"] == "body")
        params = [p["text"] for p in body_comp["parameters"]]
        assert "Dr. Anita Desai" in params
        assert any("5,000" in p for p in params)
        print(f"✓ send_whatsapp_80g_receipt generated valid Meta Cloud API template 'receipt_80g_issued' for +919876543210")

    asyncio.run(run_whatsapp_test())


def http_get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def http_post(url, data=None):
    body = json.dumps(data).encode() if data is not None else b"{}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def http_patch(url, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="PATCH")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def test_live_api_integration():
    print("\n--- Testing Live FastAPI Backend (http://localhost:8000) ---")
    base_url = "http://localhost:8000/api"

    # 1. Health
    status, h = http_get(f"{base_url}/health")
    assert status == 200
    print(f"✓ Health Check: {h}")

    # 2. Reconciliation Stats with Fraud Flagged Count
    status, stats = http_get(f"{base_url}/reconciliation/stats")
    assert status == 200
    assert "fraud_flagged_count" in stats
    print(f"✓ Reconciliation Stats: Total={stats['total_donations']}, Matched={stats['matched_count']}, Fraud Flagged={stats['fraud_flagged_count']}")

    # 3. Bank Statement Audit Report Endpoint
    status, audit_data = http_get(f"{base_url}/bank-statement/audit-report")
    assert status == 200
    assert "total_entries" in audit_data
    assert "entries_with_math_discrepancies" in audit_data
    print(f"✓ Statement Audit Report: Total Entries={audit_data['total_entries']}, Discrepancies={audit_data['entries_with_math_discrepancies']}")

    # 4. Double-Issuance Blocking Test
    status, donations = http_get(f"{base_url}/donations/")
    verified_donations = [d for d in donations if d.get("is_verified") and d.get("extracted_utr")]
    if verified_donations:
        verified_utr = verified_donations[0]["extracted_utr"]
        print(f"Testing double-issuance guard on verified UTR '{verified_utr}'...")
        unverified = [d for d in donations if not d.get("is_verified")]
        if unverified:
            target_id = unverified[0]["id"]
            http_patch(f"{base_url}/donations/{target_id}", {"extracted_utr": verified_utr})
            status, ver_err = http_post(f"{base_url}/donations/{target_id}/verify", {"verified_by_user": "auditor@test.com"})
            assert status == 400, f"Expected 400 for double issuance, got {status}"
            assert "Double issuance blocked!" in ver_err["detail"]
            print(f"✓ Double 80G Issuance blocked successfully with 400: '{ver_err['detail']}'")

    print("\nAll Anti-Fraud, Mathematical Audit, Normalization, and CA Audit tests PASSED successfully!")

if __name__ == "__main__":
    test_module_1_anti_fraud()
    test_module_2_statement_verifier()
    test_module_3_validators_and_whatsapp()
    test_live_api_integration()
