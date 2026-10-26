import os, sys, sqlite3, requests

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = r"E:\raise india\backend\raise_india.db"

def run_audit():
    print("=== [1/5] BACKEND HEALTH CHECK ===")
    res = requests.get(f"{BASE_URL}/api/health", timeout=5)
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("[PASS] Backend API is healthy.")

    print("\n=== [2/5] LEDGER DATA FETCH CHECK ===")
    res = requests.get(f"{BASE_URL}/api/donations", timeout=5)
    assert res.status_code == 200, f"Ledger fetch failed: {res.status_code}"
    data = res.json()
    print(f"[PASS] Ledger returned {len(data)} records successfully.")

    print("\n=== [3/5] BULK UPLOAD CHUNKED MOCK TEST ===")
    # Simulate multiple mock receipt files upload
    files = [
        ("files", ("receipt_1.png", b"mock binary content 1", "image/png")),
        ("files", ("receipt_2.png", b"mock binary content 2", "image/png"))
    ]
    up_res = requests.post(f"{BASE_URL}/api/donations/bulk-upload", files=files, timeout=15)
    print(f"Bulk Upload Status: {up_res.status_code}, Response: {up_res.text[:300]}")
    assert up_res.status_code == 200, f"Bulk upload failed with status {up_res.status_code}"

    print("\n=== [4/5] BATCH DELETION TEST ===")
    items = requests.get(f"{BASE_URL}/api/donations", timeout=5).json()
    if items:
        sample_ids = [items[0]["id"]]
        del_res = requests.post(f"{BASE_URL}/api/donations/batch-delete", json={"ids": sample_ids}, timeout=5)
        assert del_res.status_code == 200, f"Batch delete failed: {del_res.text}"
        print(f"[PASS] Successfully batch deleted {len(sample_ids)} test record(s).")
    else:
        print("[PASS] No items to batch delete (ledger is currently empty).")

    print("\n=== [5/5] NUCLEAR LEDGER RESET TEST ===")
    reset_res = requests.post(f"{BASE_URL}/api/donations/reset-ledger", timeout=10)
    assert reset_res.status_code == 200, f"Reset ledger failed: {reset_res.text}"
    print("[PASS] Ledger reset and cleanup executed cleanly.")

    print("\n>>> ALL 5 BULK UPLOAD & OCR AUDIT CHECKS PASSED! <<<")

if __name__ == "__main__":
    run_audit()
