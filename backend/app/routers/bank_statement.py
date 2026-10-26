from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os, re, sqlite3, shutil
import pandas as pd
from datetime import datetime

router = APIRouter(prefix="/bank-statement", tags=["Bank Statement"])

@router.post("/upload")
async def upload_bank_statement(file: UploadFile = File(...)):
    upload_dir = r"E:\raise india\backend\uploads\statements"
    os.makedirs(upload_dir, exist_ok=True)
    safe_filename = os.path.basename(file.filename or "statement.xlsx")
    temp_path = os.path.join(upload_dir, safe_filename)

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ext = os.path.splitext(safe_filename)[1].lower()
    df = None
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(temp_path)
    else:
        for enc in ['utf-8', 'latin-1', 'cp1252', 'utf-8-sig']:
            try:
                df = pd.read_csv(temp_path, encoding=enc, dtype=str)
                break
            except Exception:
                continue

    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="Statement error: File is empty or unreadable.")

    # Strip leading/trailing single quotes ('), whitespace, and newlines from all cell strings and column headers
    df.columns = [str(c).strip("' \t\r\n") for c in df.columns]
    try:
        df = df.map(lambda x: str(x).strip("' \t\r\n") if pd.notna(x) else "")
    except Exception:
        df = df.applymap(lambda x: str(x).strip("' \t\r\n") if pd.notna(x) else "")

    bank_credits = {}

    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        row_str = " ".join([str(v) for v in row_dict.values()])

        status_val = str(row_dict.get('Status', '') or row_dict.get('status', '')).upper()
        if 'FAIL' in status_val or 'CANCEL' in status_val:
            continue

        # Extract Amount: Amount, Settled_Amount, Payment_Amount, Credit, or Deposit
        amt = 0.0
        for k, v in row_dict.items():
            k_clean = str(k).strip("' \t\r\n").lower()
            if k_clean in ['amount', 'settled_amount', 'payment_amount', 'credit', 'deposit']:
                if v:
                    try:
                        parsed_amt = float(re.sub(r'[^0-9.]', '', str(v)))
                        if parsed_amt > 0:
                            amt = parsed_amt
                            break
                    except Exception:
                        pass

        # Extract Date: Transaction_Date or Settled_Date
        date_str = ""
        for k, v in row_dict.items():
            k_clean = str(k).strip("' \t\r\n").lower()
            if k_clean in ['transaction_date', 'settled_date', 'txn_date', 'date']:
                if v:
                    date_str = str(v).split(' ')[0]
                    break
        if not date_str:
            date_str = datetime.now().strftime("%d-%m-%Y")

        # Extract 12-digit UTR from Bank_Transaction_ID, RRN, Reference_Transaction_ID, UTR_No. or fallback \b[0-9]{12}\b
        found_utrs = []
        for k, v in row_dict.items():
            k_clean = str(k).strip("' \t\r\n").lower()
            if k_clean in ['bank_transaction_id', 'rrn', 'reference_transaction_id', 'utr_no.', 'utr_no', 'utr']:
                if v:
                    found_utrs.extend(re.findall(r'\b[0-9]{12}\b', str(v)))

        found_utrs.extend(re.findall(r'\b[0-9]{12}\b', row_str))

        donor_name = ""
        for k, v in row_dict.items():
            k_clean = str(k).strip("' \t\r\n").lower()
            if k_clean in ['customer_vpa', 'merchant_name', 'customer_name', 'payer_name', 'donor_name']:
                if v:
                    donor_name = str(v)
                    break
        if not donor_name:
            donor_name = "Donor"

        for u in set(found_utrs):
            bank_credits[u] = {
                "amount": amt,
                "date": date_str,
                "donor_name": donor_name
            }

    if not bank_credits:
        raise HTTPException(status_code=400, detail="Statement error: No 12-digit transaction UTRs found in uploaded file.")

    # Match in DB
    db_path = r"E:\raise india\backend\raise_india.db"
    conn = sqlite3.connect(db_path, timeout=30.0)
    cursor = conn.cursor()

    cursor.execute("SELECT id, extracted_utr, extracted_amount, screenshot_url FROM donations")
    donations = cursor.fetchall()

    matched_list = []
    matched_count = 0
    fake_count = 0

    for d_id, utr, amt, img_url in donations:
        clean_utr = str(utr).strip() if utr else None
        
        if clean_utr and clean_utr in bank_credits:
            credit_info = bank_credits[clean_utr]
            cursor.execute("""
                UPDATE donations
                SET status = 'MATCHED',
                    is_verified = 1,
                    is_flagged_fraud = 0,
                    flagged_reason = NULL,
                    bank_matched_mode = '12_DIGIT_STATEMENT_MATCH',
                    matched_statement_id = ?,
                    verified_at = ?
                WHERE id = ?
            """, (file.filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), d_id))

            matched_count += 1
            raw_receipt = os.path.basename(img_url) if img_url else "Receipt"
            clean_receipt_name = re.sub(
                r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}_',
                '',
                raw_receipt
            )
            formatted_utr = str(clean_utr).zfill(12)

            matched_list.append({
                "Clean Receipt File": clean_receipt_name,
                "Bank Statement File": file.filename or "file.xlsx",
                "12-Digit UTR": formatted_utr,
                "Verified Amount (₹)": amt or credit_info["amount"],
                "Bank Credit Date": credit_info["date"],
                "Donor / Payer Name": credit_info["donor_name"],
                "Status": "MATCHED & VERIFIED"
            })
        else:
            cursor.execute("""
                UPDATE donations
                SET status = 'REJECTED',
                    is_verified = 0,
                    is_flagged_fraud = 1,
                    flagged_reason = 'FAKE PROOF: 12-digit UTR not found in bank credit statement.',
                    matched_statement_id = NULL
                WHERE id = ?
            """, (d_id,))
            fake_count += 1

    conn.commit()
    conn.close()

    # Save Excel report strictly with required columns
    export_dir = r"E:\raise india\backend\uploads"
    excel_path = os.path.join(export_dir, "reconciled_verified_donations.xlsx")
    os.makedirs(export_dir, exist_ok=True)

    export_columns = [
        "Clean Receipt File",
        "Bank Statement File",
        "12-Digit UTR",
        "Verified Amount (₹)",
        "Bank Credit Date",
        "Donor / Payer Name",
        "Status"
    ]

    if matched_list:
        df_export = pd.DataFrame(matched_list)
        df_export = df_export[export_columns]
        df_export.to_excel(excel_path, index=False)
    else:
        pd.DataFrame(columns=export_columns).to_excel(excel_path, index=False)

    return {
        "success": True,
        "message": f"Auto-Match Complete: {matched_count} Matched (SUCCESS), {fake_count} Unmatched (FLAGGED FAKE).",
        "matched_count": matched_count,
        "fake_count": fake_count
    }

@router.get("/download-matched")
def download_matched_excel():
    excel_path = r"E:\raise india\backend\uploads\reconciled_verified_donations.xlsx"
    if os.path.exists(excel_path):
        return FileResponse(excel_path, filename="reconciled_verified_donations.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    raise HTTPException(status_code=404, detail="No matched Excel file found.")
