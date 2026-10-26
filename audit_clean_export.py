import os, sys, sqlite3, requests, re
import pandas as pd

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if r"E:\raise india" not in sys.path:
    sys.path.insert(0, r"E:\raise india")

def run_audit():
    print("=== [1/5] DATABASE INTEGRITY AUDIT ===")
    conn = sqlite3.connect(r"E:\raise india\backend\raise_india.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM donations")
    total_db = cur.fetchone()[0]
    print(f"Total donations in DB: {total_db}")
    assert total_db > 0, "Audit Fail: DB has 0 records."

    print("\n=== [2/5] API HEALTH & SERIALIZATION AUDIT ===")
    res = requests.get("http://127.0.0.1:8000/api/donations")
    print(f"GET /api/donations Status: {res.status_code}")
    assert res.status_code == 200, f"Audit Fail: Expected HTTP 200, got {res.status_code}"
    data = res.json()
    print(f"API returned {len(data)} serialized donation records.")

    print("\n=== [3/5] STATEMENT RECONCILIATION AUDIT ===")
    sample_file = r"E:\raise india\file.xlsx"
    if os.path.exists(sample_file):
        with open(sample_file, "rb") as f:
            recon_res = requests.post(
                "http://127.0.0.1:8000/api/bank-statement/upload",
                files={"file": (os.path.basename(sample_file), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )
        print(f"Reconciliation Status: {recon_res.status_code}")
        assert recon_res.status_code == 200, f"Statement reconciliation failed: {recon_res.text}"
        payload = recon_res.json()
        print(f"Result: {payload.get('message')}")

    print("\n=== [4/5] EXCEL CLEAN DATA INTEGRITY AUDIT ===")
    report_path = r"E:\raise india\backend\uploads\reconciled_verified_donations.xlsx"
    assert os.path.exists(report_path), "Audit Fail: Reconciled Excel file missing."
    df = pd.read_excel(report_path, dtype={'12-Digit UTR': str})
    print(f"Export rows count: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    # Column existence assertion
    expected_cols = [
        "Clean Receipt File",
        "Bank Statement File",
        "12-Digit UTR",
        "Verified Amount (₹)",
        "Bank Credit Date",
        "Donor / Payer Name",
        "Status"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Audit Fail: Missing column '{col}' in export."

    # Validate UUID stripping on receipt names
    uuid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-')
    for val in df["Clean Receipt File"].dropna():
        assert not uuid_pattern.match(str(val)), f"Audit Fail: File name contains unstripped UUID: {val}"

    # Validate 12-digit UTR length preserving leading zeros
    for utr in df["12-Digit UTR"].dropna():
        assert len(str(utr)) == 12, f"Audit Fail: UTR '{utr}' does not have exactly 12 digits."

    # Validate statement file tracking
    for stmt_name in df["Bank Statement File"].dropna():
        assert "file.xlsx" in str(stmt_name), f"Audit Fail: Incorrect statement file tracked: {stmt_name}"

    print("[SUCCESS] All data rows formatted, cleaned, and validated.")

    print("\n=== [5/5] DOWNLOAD ENDPOINT AUDIT ===")
    dl_res = requests.get("http://127.0.0.1:8000/api/bank-statement/download-matched")
    print(f"Download Endpoint Status: {dl_res.status_code}")
    assert dl_res.status_code == 200, f"Download failed with status {dl_res.status_code}"
    assert len(dl_res.content) > 0, "Downloaded file payload is empty."

    print("\n>>> ALL 5 AUDIT STAGES PASSED WITH ZERO ERRORS! <<<")

if __name__ == "__main__":
    run_audit()
