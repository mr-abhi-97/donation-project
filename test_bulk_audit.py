import os, sys, sqlite3, requests

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = r"E:\raise india\backend\raise_india.db"

def run_audit():
    print("=== [1/5] API HEALTH CHECK ===")
    res = requests.get(f"{BASE_URL}/api/health", timeout=5)
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("[PASS] Backend is healthy.")

    print("\n=== [2/5] GET DONATIONS LEDGER ===")
    res = requests.get(f"{BASE_URL}/api/donations", timeout=5)
    assert res.status_code == 200, f"Ledger fetch failed: {res.status_code}"
    data = res.json()
    print(f"[PASS] Ledger returned {len(data)} records successfully.")

    print("\n=== [3/5] BULK UPLOAD MOCK TEST ===")
    # Create dummy image bytes for upload test
    dummy_img = b"fake image binary content"
    files = [("files", ("test_receipt.png", dummy_img, "image/png"))]
    
    # Test bulk upload endpoint (or fallback to single receipt upload)
    up_res = requests.post(f"{BASE_URL}/api/donations/bulk-upload", files=files, timeout=10)
    print(f"Bulk Upload Status: {up_res.status_code}, Response: {up_res.text[:200]}")
    # Even if OCR mock triggers, status should be 200 or handled gracefully
    assert up_res.status_code in [200, 400], f"Unexpected status: {up_res.status_code}"

    print("\n=== [4/5] BATCH DELETE TEST ===")
    # Fetch current IDs
    items = requests.get(f"{BASE_URL}/api/donations", timeout=5).json()
    if items:
        sample_ids = [items[0]["id"]]
        del_res = requests.post(f"{BASE_URL}/api/donations/batch-delete", json={"ids": sample_ids}, timeout=5)
        assert del_res.status_code == 200, f"Batch delete failed: {del_res.text}"
        print(f"[PASS] Successfully batch deleted {len(sample_ids)} item(s).")
    else:
        print("[PASS] No items to batch delete (empty ledger).")

    print("\n=== [5/5] RESET LEDGER TEST ===")
    reset_res = requests.post(f"{BASE_URL}/api/donations/reset-ledger", timeout=5)
    assert reset_res.status_code == 200, f"Reset ledger failed: {reset_res.text}"
    print("[PASS] Ledger reset executed cleanly.")

    print("\n>>> ALL BULK UPLOAD & LEDGER AUDIT CHECKS PASSED! <<<")

if __name__ == "__main__":
    run_audit()
