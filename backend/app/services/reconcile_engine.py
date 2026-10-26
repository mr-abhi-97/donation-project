import os
import re
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.models import Donation

def process_and_reconcile_statement(file_path: str, db: Session):
    # 1. Read file as CSV or Excel
    ext = os.path.splitext(file_path)[1].lower()
    df = None
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
    else:
        # Try multiple encodings and separators
        for enc in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(file_path, encoding=enc)
                break
            except Exception:
                continue

    if df is None or df.empty:
        raise ValueError("Bank statement file is empty or unreadable.")

    # Standardize column headers (lower case, stripped)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Detect narration/description column
    narration_cols = [c for c in df.columns if any(k in c for k in ['narration', 'description', 'particular', 'remarks', 'details', 'txn'])]
    narration_col = narration_cols[0] if narration_cols else df.columns[0]

    # Detect credit/deposit/amount column
    credit_cols = [c for c in df.columns if any(k in c for k in ['credit', 'cr', 'deposit', 'received', 'amt', 'amount'])]
    credit_col = credit_cols[0] if credit_cols else None

    # Detect date column
    date_cols = [c for c in df.columns if any(k in c for k in ['date', 'txn date', 'value date'])]
    date_col = date_cols[0] if date_cols else None

    # Extract all 12-digit UTRs from the bank statement
    bank_credits = {}
    for idx, row in df.iterrows():
        row_str = " ".join([str(val) for val in row.values])
        
        # Check credit amount if column exists
        credit_val = 0.0
        if credit_col and pd.notna(row[credit_col]):
            try:
                credit_val = float(str(row[credit_col]).replace(',', '').replace('₹', '').strip())
            except Exception:
                credit_val = 0.0

        # Find 12-digit UTR in whole row text or narration
        utr_matches = re.findall(r'\b[0-9]{12}\b', row_str)
        txn_date = str(row[date_col]) if date_col and pd.notna(row[date_col]) else datetime.now().strftime("%d-%m-%Y")

        for u in utr_matches:
            bank_credits[u] = {
                "amount": credit_val,
                "date": txn_date,
                "raw_narration": str(row.get(narration_col, ""))
            }

    if not bank_credits:
        # Fallback: if no 12-digit UTR found, search all numbers >= 6 digits
        for idx, row in df.iterrows():
            row_str = " ".join([str(val) for val in row.values])
            nums = re.findall(r'\b[0-9]{6,16}\b', row_str)
            for n in nums:
                bank_credits[n] = {
                    "amount": 0.0,
                    "date": datetime.now().strftime("%d-%m-%Y"),
                    "raw_narration": row_str
                }

    print(f"[RECON] Found {len(bank_credits)} potential transaction entries in Bank Statement.")

    # 2. Match with Donations in DB
    donations = db.query(Donation).all()
    matched_list = []
    matched_count = 0
    fake_count = 0

    for d in donations:
        utr = getattr(d, 'extracted_utr', None) or getattr(d, 'utr', None)
        
        if not utr:
            d.status = "REJECTED"
            d.flagged_reason = "FAKE_PROOF: No UTR could be extracted from image."
            d.is_flagged_fraud = True
            fake_count += 1
            continue

        if utr in bank_credits:
            # MATCH SUCCESSFUL
            d.status = "MATCHED"
            d.is_verified = True
            d.is_flagged_fraud = False
            d.flagged_reason = None
            d.bank_matched_mode = "12_DIGIT_EXACT_MATCH"
            d.verified_at = datetime.now()
            d.matched_statement_id = "STATEMENT_" + datetime.now().strftime("%Y%m%d%H%M")
            matched_count += 1

            donor_name = getattr(d, 'donor_name', '') or getattr(d, 'payer_name', '') or 'Donor'
            amt = getattr(d, 'extracted_amount', 0) or getattr(d, 'amount', 0)
            date_val = bank_credits[utr]["date"]

            matched_list.append({
                "Donor / Payer Name": donor_name,
                "12-Digit UTR": utr,
                "Reconciled Amount (₹)": amt,
                "Bank Credit Date": date_val,
                "Status": "VERIFIED & CREDITED"
            })
        else:
            # NOT FOUND IN STATEMENT -> MARK AS FAKE / FRAUD
            d.status = "REJECTED"
            d.is_verified = False
            d.is_flagged_fraud = True
            d.flagged_reason = "FAKE / FRAUD: 12-digit UTR not found in official bank statement credit records."
            fake_count += 1

    db.commit()

    # 3. Save Matched Donations directly to Excel file
    excel_export_path = r"E:\raise india\backend\uploads\reconciled_verified_donations.xlsx"
    os.makedirs(os.path.dirname(excel_export_path), exist_ok=True)

    if matched_list:
        matched_df = pd.DataFrame(matched_list)
        matched_df.to_excel(excel_export_path, index=False)
        print(f"[SUCCESS] Excel report saved to: {excel_export_path}")
    else:
        # Create empty template if zero matched
        pd.DataFrame(columns=["Donor / Payer Name", "12-Digit UTR", "Reconciled Amount (₹)", "Bank Credit Date", "Status"]).to_excel(excel_export_path, index=False)

    return {
        "matched": matched_count,
        "fake_unmatched": fake_count,
        "excel_path": excel_export_path
    }