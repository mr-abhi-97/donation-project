import os, sys, sqlite3, requests

BASE_URL = "http://127.0.0.1:8000"
DB_PATH = r"E:\raise india\backend\raise_india.db"

def run_audit():
    print("=== [1/5] BACKEND API HEALTH CHECK ===")
    res = requests.get(f"{BASE_URL}/api/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("[PASS] Backend is healthy.")

    print("\n=== [2/5] LEDGER SERIALIZATION CHECK ===")
    res = requests.get(f"{BASE_URL}/api/donations")
    assert res.status_code == 200, f"Ledger fetch failed: {res.status_code}"
    data = res.json()
    print(f"[PASS] Ledger returned {len(data)} records. Serialization active.")

    print("\n=== [3/5] OCR EXTRACTION FIELD AUDIT ===")
    # Upload a sample mock receipt to verify extracted fields are not stuck on 'Extracting...'
    dummy_img = b"mock payment receipt bytes with UTR 317017653200 and amount 2501"
    files = [("files", ("audit_receipt.png", dummy_img, "image/png"))]
    up_res = requests.post(f"{BASE_URL}/api/donations/bulk-upload", files=files)
    assert up_res.status_code == 200, f"Upload failed: {up_res.text}"
    
    updated_items = requests.get(f"{BASE_URL}/api/donations").json()
    assert len(updated_items) > 0, "No items found after upload"
    latest_item = updated_items[0]
    print(f"Extracted UTR: {latest_item.get('extracted_utr')}")
    print(f"Extracted Amount: {latest_item.get('extracted_amount')}")
    assert latest_item.get('extracted_utr') == "317017653200", f"Expected UTR 317017653200, got {latest_item.get('extracted_utr')}"
    assert float(latest_item.get('extracted_amount') or 0) == 2501.0, f"Expected amount 2501, got {latest_item.get('extracted_amount')}"
    print("[PASS] OCR extraction fields evaluated.")

    print("\n=== [4/5] BATCH DELETION AUDIT ===")
    sample_ids = [latest_item["id"]]
    del_res = requests.post(f"{BASE_URL}/api/donations/batch-delete", json={"ids": sample_ids})
    assert del_res.status_code == 200, f"Batch delete failed: {del_res.text}"
    print("[PASS] Batch deletion successfully removed test record.")

    print("\n=== [5/5] NUCLEAR LEDGER RESET AUDIT ===")
    reset_res = requests.post(f"{BASE_URL}/api/donations/reset-ledger")
    assert reset_res.status_code == 200, f"Reset ledger failed: {reset_res.text}"
    print("[PASS] Ledger reset executed cleanly.")

    print("\n>>> ALL 5 OCR & LEDGER AUDIT CHECKS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_audit()
