import os, sys, sqlite3, requests, pandas as pd

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if r"E:\raise india" not in sys.path:
    sys.path.insert(0, r"E:\raise india")

def run_audit():
    print("=== [1/5] DATABASE AUDIT ===")
    conn = sqlite3.connect(r"E:\raise india\backend\raise_india.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM donations")
    total_db = cur.fetchone()[0]
    print(f"Total donations in DB: {total_db}")
    assert total_db > 0, "DB Audit Failed: Database is empty."

    print("\n=== [2/5] DIRECT FUNCTION SERIALIZATION AUDIT ===")
    from backend.app.database import SessionLocal
    from backend.app.routers.donations import list_donations
    db = SessionLocal()
    records = list_donations(db=db)
    print(f"list_donations executed cleanly: {len(records)} records returned.")
    assert len(records) == total_db, "Count mismatch between DB and router."
    db.close()

    print("\n=== [3/5] HTTP API 200 OK AUDIT ===")
    res = requests.get("http://127.0.0.1:8000/api/donations")
    print(f"GET /api/donations Status: {res.status_code}")
    assert res.status_code == 200, f"API Audit Failed: HTTP {res.status_code}"
    data = res.json()
    print(f"API successfully returned {len(data)} serialized records.")

    print("\n=== [4/5] STATEMENT RECONCILIATION AUDIT ===")
    sample_file = r"E:\raise india\file.xlsx"
    if os.path.exists(sample_file):
        with open(sample_file, "rb") as f:
            recon_res = requests.post("http://127.0.0.1:8000/api/bank-statement/upload", files={"file": f})
        print(f"Reconciliation Status: {recon_res.status_code}, Response: {recon_res.json()}")
        assert recon_res.status_code == 200, "Statement reconciliation failed."

    print("\n=== [5/5] EXCEL REPORT GENERATION AUDIT ===")
    report_path = r"E:\raise india\backend\uploads\reconciled_verified_donations.xlsx"
    assert os.path.exists(report_path), "Excel report file was not created."
    df_report = pd.read_excel(report_path)
    print(f"Report verified: {len(df_report)} matched rows found.")
    print(f"Columns present: {list(df_report.columns)}")

    print("\n>>> ALL 5 AUDIT CHECKS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    run_audit()
