from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os, re, sqlite3, shutil
import pandas as pd
from datetime import datetime

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])

@router.post("/match")
async def reconcile_bank_statement(file: UploadFile = File(...)):
    upload_dir = r"E:\raise india\backend\uploads\statements"
    os.makedirs(upload_dir, exist_ok=True)
    temp_path = os.path.join(upload_dir, file.filename)

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 1. Read CSV/Excel safely
    ext = os.path.splitext(file.filename)[1].lower()
    df = None
    if ext in ['.xlsx', '.xls']:
        df = pd.read_excel(temp_path)
    else:
        for enc in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(temp_path, encoding=enc, dtype=str)
                break
            except Exception:
                continue

    if df is None or df.empty:
        raise HTTPException(status_code=400, detail="Uploaded statement is empty or invalid.")

    # Clean single quotes and whitespace from all columns and headers
    df.columns = [re.sub(r"[^a-zA-Z0-9_]", "", str(c).strip().lower()) for c in df.columns]
    try:
        df = df.map(lambda x: str(x).strip("' \t\r\n") if pd.notna(x) else "")
    except Exception:
        df = df.applymap(lambda x: str(x).strip("' \t\r\n") if pd.notna(x) else "")

    print(f"[RECON] Loaded statement with {len(df)} rows and columns: {list(df.columns)}")

    # 2. Extract Bank Credits (Supports Paytm PG, HDFC, SBI, ICICI, etc.)
    bank_credits = {}
    
    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        row_str = " ".join([str(v) for v in row_dict.values()])

        # Check status if PG sheet
        status_val = str(row_dict.get('status', '') or row_dict.get('transacticstatus', '')).upper()
        if 'FAILURE' in status_val or 'FAILED' in status_val:
            continue

        # Extract Amount
        amt = 0.0
        for amt_key in ['amount', 'paymentamount', 'credit', 'deposit', 'cr', 'settledamount']:
            if amt_key in row_dict and row_dict[amt_key]:
                try:
                    amt = float(re.sub(r'[^0-9.]', '', str(row_dict[amt_key])))
                    if amt > 0:
                        break
                except Exception:
                    pass

        # Extract Date
        date_str = datetime.now().strftime("%d-%m-%Y")
        for date_key in ['transactidate', 'settledd', 'payoutd', 'date', 'updateddate']:
            if date_key in row_dict and row_dict[date_key]:
                date_str = str(row_dict[date_key]).split(' ')[0]
                break

        # Find any 12-digit UTR in whole row or specific UTR columns
        utrs_in_row = []
        for col_name, val in row_dict.items():
            if any(k in col_name for k in ['utr', 'bank', 'ref', 'rrn', 'order', 'external']):
                found = re.findall(r'[0-9]{12}', str(val))
                utrs_in_row.extend(found)
        
        # Also regex the entire raw row string
        utrs_in_row.extend(re.findall(r'\b[0-9]{12}\b', row_str))

        for u in set(utrs_in_row):
            bank_credits[u] = {
                "amount": amt,
                "date": date_str,
                "source": "PAYTM_PG / BANK_STATEMENT"
            }

    if not bank_credits:
        raise HTTPException(
            status_code=400,
            detail="Statement error: No 12-digit UTR or transaction numbers found in the uploaded statement."
        )

    print(f"[RECON] Successfully extracted {len(bank_credits)} unique transaction references.")

    # 3. Match against Database
    db_path = r"E:\raise india\backend\raise_india.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, extracted_utr, extracted_amount, screenshot_url FROM donations")
    donations = cursor.fetchall()

    matched_list = []
    matched_count = 0
    fake_count = 0

    for d_id, utr, amt, img_url in donations:
        if utr and str(utr).strip() in bank_credits:
            # MATCHED -> Set to SUCCESS / MATCHED
            cursor.execute("""
                UPDATE donations
                SET status = 'MATCHED',
                    is_verified = 1,
                    is_flagged_fraud = 0,
                    flagged_reason = NULL,
                    bank_matched_mode = '12_DIGIT_PG_MATCH',
                    matched_statement_id = ?,
                    verified_at = ?
                WHERE id = ?
            """, (file.filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), d_id))

            matched_count += 1
            credit_info = bank_credits[str(utr).strip()]
            matched_list.append({
                "Receipt File": os.path.basename(img_url) if img_url else "Receipt",
                "12-Digit UTR": utr,
                "Verified Amount (₹)": amt or credit_info["amount"],
                "Settled / Credit Date": credit_info["date"],
                "Reconciliation Status": "MATCHED & VERIFIED"
            })
        else:
            # UNMATCHED -> Set to REJECTED / FAKE
            cursor.execute("""
                UPDATE donations
                SET status = 'REJECTED',
                    is_verified = 0,
                    is_flagged_fraud = 1,
                    flagged_reason = 'FAKE PROOF: 12-digit UTR not found in official bank/Paytm credit statement.'
                WHERE id = ?
            """, (d_id,))
            fake_count += 1

    conn.commit()
    conn.close()

    # 4. Generate Matched Excel Report
    export_dir = r"E:\raise india\backend\uploads"
    excel_path = os.path.join(export_dir, "reconciled_verified_donations.xlsx")
    os.makedirs(export_dir, exist_ok=True)

    if matched_list:
        pd.DataFrame(matched_list).to_excel(excel_path, index=False)
    else:
        pd.DataFrame(columns=["Receipt File", "12-Digit UTR", "Verified Amount (₹)", "Settled / Credit Date", "Reconciliation Status"]).to_excel(excel_path, index=False)

    return {
        "success": True,
        "message": f"Auto-Reconciliation Complete: {matched_count} Matched (SUCCESS), {fake_count} Unmatched (FLAGGED FAKE).",
        "matched_count": matched_count,
        "fake_count": fake_count
    }

@router.get("/download-matched")
def download_matched_excel():
    excel_path = r"E:\raise india\backend\uploads\reconciled_verified_donations.xlsx"
    if os.path.exists(excel_path):
        return FileResponse(excel_path, filename="reconciled_verified_donations.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    raise HTTPException(status_code=404, detail="No reconciled report generated yet.")
