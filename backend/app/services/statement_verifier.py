import io
from typing import Dict, Any, List, Optional
import pandas as pd
from pypdf import PdfReader


class StatementAuditor:
    # Known consumer / desktop document editing utilities indicating tampering
    SUSPICIOUS_TOOLS = [
        "photoshop", "canva", "ilovepdf", "word", "writer", "excel",
        "acrobat distiller", "foxit", "pdf2go", "smallpdf", "sejda",
        "nitro", "libreoffice", "gimp", "inkscape", "coreldraw",
        "wondershare", "pdfcreator", "preview"
    ]

    # Authentic banking / enterprise core financial report generators
    CORE_BANKING_PRODUCERS = [
        "finacle", "oracle", "jasper", "itext", "cbs", "infosys",
        "bancs", "flexcube", "fiserv", "temenos", "apache fop",
        "crystal reports", "openpdf", "ibm filenet"
    ]

    @classmethod
    def audit_pdf_metadata(cls, file_bytes: bytes) -> dict:
        """
        Inspects PDF metadata headers (/Creator, /Producer, /Author) to detect
        if the statement was manipulated using desktop editing tools (Photoshop, Canva, Word, iLovePDF)
        instead of originating from legitimate core banking software (Finacle, Oracle, Jasper, iText).
        """
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            metadata = reader.metadata or {}

            creator = str(metadata.get("/Creator", "") or "").strip()
            producer = str(metadata.get("/Producer", "") or "").strip()
            author = str(metadata.get("/Author", "") or "").strip()

            combined_str = f"{creator} {producer} {author}".lower()

            flags = []
            is_suspicious = False

            # Check for suspicious editing utilities
            for tool in cls.SUSPICIOUS_TOOLS:
                if tool in combined_str:
                    flags.append(f"Suspicious editing tool detected in metadata: '{tool}'")
                    is_suspicious = True

            # Check if any legitimate core banking producer is recognized
            has_core_banking = any(cb in combined_str for cb in cls.CORE_BANKING_PRODUCERS)
            
            # If empty metadata or desktop tool without core banking signature
            if not creator and not producer:
                flags.append("PDF metadata stripped or empty (potential anonymization)")
                # Not definitively suspicious on its own, but noteworthy

            return {
                "creator": creator,
                "producer": producer,
                "author": author,
                "is_suspicious": is_suspicious,
                "has_core_banking_signature": has_core_banking,
                "flags": flags
            }
        except Exception as e:
            return {
                "creator": "",
                "producer": "",
                "author": "",
                "is_suspicious": False,
                "has_core_banking_signature": False,
                "flags": [f"Could not parse PDF metadata: {str(e)}"]
            }

    @classmethod
    def audit_running_balance(cls, df: pd.DataFrame) -> dict:
        """
        Verifies mathematical continuity row-by-row:
        Balance(N) = Balance(N-1) + Deposit(N) - Withdrawal(N)
        
        Tolerance: ₹0.05
        Flags rogue or manually inserted rows.
        """
        if df.empty:
            return {
                "is_math_valid": True,
                "broken_rows": [],
                "total_discrepancies": 0
            }

        # Normalize column names
        col_map = {}
        for col in df.columns:
            c = str(col).strip().lower().replace("_", " ")
            if any(k in c for k in ["balance", "closing balance", "bal", "running balance"]):
                if "balance" not in col_map:
                    col_map["balance"] = col
            elif any(k in c for k in ["credit", "credit amount", "deposit", "deposit amount", "cr"]):
                if "credit" not in col_map:
                    col_map["credit"] = col
            elif any(k in c for k in ["debit", "debit amount", "withdrawal", "withdrawal amount", "dr"]):
                if "debit" not in col_map:
                    col_map["debit"] = col
            elif any(k in c for k in ["narration", "particulars", "description", "details"]):
                if "narration" not in col_map:
                    col_map["narration"] = col
            elif any(k in c for k in ["date", "txn date", "transaction date"]):
                if "date" not in col_map:
                    col_map["date"] = col

        if "balance" not in col_map or "credit" not in col_map:
            # Cannot mathematically audit without both balance and credit columns
            return {
                "is_math_valid": True,
                "broken_rows": [],
                "total_discrepancies": 0,
                "note": "Running balance check skipped: Statement lacks explicit balance or credit column"
            }

        broken_rows = []
        prev_balance: Optional[float] = None

        for idx, row in df.iterrows():
            # Parse balance
            bal_raw = row.get(col_map["balance"])
            if pd.isna(bal_raw):
                continue

            try:
                current_balance = float(str(bal_raw).replace(",", "").replace("₹", "").strip())
            except Exception:
                continue

            # Parse credit / deposit
            credit_raw = row.get(col_map["credit"], 0.0)
            try:
                credit_amt = float(str(credit_raw).replace(",", "").replace("₹", "").strip()) if pd.notna(credit_raw) else 0.0
            except Exception:
                credit_amt = 0.0

            # Parse debit / withdrawal
            debit_amt = 0.0
            if "debit" in col_map:
                debit_raw = row.get(col_map["debit"], 0.0)
                try:
                    debit_amt = float(str(debit_raw).replace(",", "").replace("₹", "").strip()) if pd.notna(debit_raw) else 0.0
                except Exception:
                    debit_amt = 0.0

            # Verify math against previous row if previous balance exists
            if prev_balance is not None:
                expected_balance = prev_balance + credit_amt - debit_amt
                discrepancy = abs(current_balance - expected_balance)

                if discrepancy > 0.05:
                    narration_val = str(row.get(col_map.get("narration", ""), f"Row {idx+1}"))
                    date_val = str(row.get(col_map.get("date", ""), ""))
                    broken_rows.append({
                        "row_index": int(idx),
                        "date": date_val,
                        "narration": narration_val,
                        "stated_balance": current_balance,
                        "expected_balance": round(expected_balance, 2),
                        "discrepancy": round(discrepancy, 2),
                        "credit_amount": credit_amt,
                        "debit_amount": debit_amt,
                        "previous_balance": prev_balance
                    })

            prev_balance = current_balance

        return {
            "is_math_valid": len(broken_rows) == 0,
            "broken_rows": broken_rows,
            "total_discrepancies": len(broken_rows)
        }
