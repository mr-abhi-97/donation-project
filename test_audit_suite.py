import os
import sys
import sqlite3
import requests
import uuid
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = str(PROJECT_ROOT / "backend" / "raise_india.db")
UPLOADS_SCREENSHOTS_DIR = PROJECT_ROOT / "backend" / "uploads" / "screenshots"

def run_audit():
    print("=" * 80)
    print(" RAISE INDIA - 5-Point Automated Audit Suite")
    print("=" * 80)

    passed = 0
    failed = 0

    # AUDIT 1: FastAPI Health Endpoint
    print("\n" + "=" * 80)
    print(" AUDIT 1: FastAPI Health Endpoint (/api/health)")
    print("=" * 80)
    try:
        res = requests.get(f"{BASE_URL}/api/health", timeout=5)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data.get("status") == "healthy", f"Expected status 'healthy', got: {data}"
        print(f" [PASS] Audit 1: Backend is healthy -> {data.get('app')} ({data.get('ngo')})")
        passed += 1
    except Exception as e:
        print(f" [FAIL] Audit 1: Health check failed: {e}")
        failed += 1

    # SETUP for Audit 2 & 3: Seed test records
    print("\n" + "=" * 80)
    print(" SETUP: Seeding test donation records for Batch Deletion")
    print("=" * 80)
    UPLOADS_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    test_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    test_files = []

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for tid in test_ids:
            fname = f"test_audit_{tid}.png"
            fpath = UPLOADS_SCREENSHOTS_DIR / fname
            with open(fpath, "w") as f:
                f.write("mock image bytes for audit")
            test_files.append(fpath)

            rel_url = f"/uploads/screenshots/{fname}"
            cur.execute("""
                INSERT INTO donations (
                    id, status, is_verified, is_flagged_fraud, screenshot_url,
                    extracted_utr, extracted_amount, created_at, updated_at
                ) VALUES (?, 'EXTRACTED', 0, 0, ?, '888888888888', 500.0, datetime('now'), datetime('now'))
            """, (tid, rel_url))
        conn.commit()
        conn.close()
        print(f" Seeded {len(test_ids)} test donation record(s) and mock screenshot file(s).")
    except Exception as e:
        print(f" [ERROR] Setup failed: {e}")
        sys.exit(1)

    # AUDIT 2: Batch Deletion API Contract
    print("\n" + "=" * 80)
    print(" AUDIT 2: Batch Deletion API Contract & Response Schema (/api/donations/batch-delete)")
    print("=" * 80)
    try:
        res = requests.post(f"{BASE_URL}/api/donations/batch-delete", json={"ids": test_ids}, timeout=10)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data.get("status") == "success" or data.get("success") is True, f"Unexpected response: {data}"
        assert data.get("deleted_count") == len(test_ids), f"Expected deleted_count {len(test_ids)}, got {data.get('deleted_count')}"
        
        # Verify from database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        placeholders = ",".join(["?"] * len(test_ids))
        cur.execute(f"SELECT COUNT(*) FROM donations WHERE id IN ({placeholders})", test_ids)
        remaining = cur.fetchone()[0]
        conn.close()
        assert remaining == 0, f"Expected 0 remaining rows in DB, found {remaining}"

        print(f" [PASS] Audit 2: Batch delete contract verified successfully ({len(test_ids)} records removed).")
        passed += 1
    except Exception as e:
        print(f" [FAIL] Audit 2: Batch delete contract failed: {e}")
        failed += 1

    # AUDIT 3: Physical Screenshot File Cleanup From Disk
    print("\n" + "=" * 80)
    print(" AUDIT 3: Physical Screenshot File Cleanup From Disk")
    print("=" * 80)
    try:
        for fpath in test_files:
            assert not fpath.exists(), f"File was not deleted from disk: {fpath}"
        print(" [PASS] Audit 3: Physical screenshot files successfully cleaned up from disk.")
        passed += 1
    except Exception as e:
        print(f" [FAIL] Audit 3: Physical file cleanup failed: {e}")
        failed += 1

    # AUDIT 4: Full Nuclear Ledger Reset
    print("\n" + "=" * 80)
    print(" AUDIT 4: Full Nuclear Ledger Reset (/api/donations/reset-ledger)")
    print("=" * 80)
    try:
        # Seed a dummy donation with all required NOT NULL columns
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        dummy_id = str(uuid.uuid4())
        dummy_fname = f"dummy_reset_{dummy_id}.png"
        dummy_fpath = UPLOADS_SCREENSHOTS_DIR / dummy_fname
        with open(dummy_fpath, "w") as f:
            f.write("mock screenshot for reset test")

        cur.execute("""
            INSERT INTO donations (
                id, status, is_verified, is_flagged_fraud, screenshot_url,
                extracted_utr, extracted_amount, created_at, updated_at
            ) VALUES (?, 'EXTRACTED', 0, 0, ?, '777777777777', 250.0, datetime('now'), datetime('now'))
        """, (dummy_id, f"/uploads/screenshots/{dummy_fname}"))
        conn.commit()
        conn.close()

        res = requests.post(f"{BASE_URL}/api/donations/reset-ledger", timeout=10)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data.get("status") == "success" or data.get("success") is True, f"Unexpected response: {data}"
        assert data.get("donations_deleted", 0) >= 1 or data.get("deleted_count", 0) >= 1

        # Verify DB is completely wiped
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for tbl in ["donations", "tax_receipts_80g", "bank_statement_entries", "donors"]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            cnt = cur.fetchone()[0]
            assert cnt == 0, f"Expected 0 rows in {tbl}, got {cnt}"
        conn.close()

        print(f" [PASS] Audit 4: Nuclear ledger reset successful -> {data.get('message')}")
        passed += 1
    except Exception as e:
        print(f" [FAIL] Audit 4: Reset ledger failed: {e}")
        failed += 1

    # AUDIT 5: Idempotent Reset Behavior on Empty Database
    print("\n" + "=" * 80)
    print(" AUDIT 5: Idempotent Reset on Empty DB (Returns 200 with Zero Counts)")
    print("=" * 80)
    try:
        res = requests.post(f"{BASE_URL}/api/donations/reset-ledger", timeout=10)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data.get("status") == "success" or data.get("success") is True, f"Unexpected response: {data}"
        assert data.get("donations_deleted", 0) == 0, f"Expected 0 donations_deleted, got {data.get('donations_deleted')}"
        assert data.get("deleted_count", 0) == 0, f"Expected 0 deleted_count, got {data.get('deleted_count')}"
        print(" [PASS] Audit 5: Idempotent reset on empty DB verified successfully (0 records deleted).")
        passed += 1
    except Exception as e:
        print(f" [FAIL] Audit 5: Idempotent reset failed: {e}")
        failed += 1

    print("\n" + "=" * 80)
    print(" AUDIT SUMMARY")
    print("=" * 80)
    print(f" Total Checks : 5")
    print(f" Passed       : {passed}")
    print(f" Failed       : {failed}")
    print("=" * 80)

    if failed > 0:
        print("\n [AUDIT FAILED] Some checks did not pass.")
        sys.exit(1)
    else:
        print("\n [AUDIT PASSED] All 5 checks passed with flying colors!")
        sys.exit(0)

if __name__ == "__main__":
    run_audit()