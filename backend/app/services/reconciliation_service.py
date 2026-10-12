import io
import re
import uuid
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import logging
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import Donation, BankStatementEntry, DonationStatus
from backend.app.schemas import FuzzyCandidateResponse, BankStatementEntryResponse, to_pydantic

logger = logging.getLogger(__name__)


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein edit distance between two strings."""
    if not s1 or not s2:
        return max(len(s1 or ""), len(s2 or ""))
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


class ReconciliationService:
    @staticmethod
    def extract_utr_from_narration(narration: str) -> Optional[str]:
        """
        Extracts 12-digit UTR from common Indian banking narrations:
        - UPI/428910293812/CR/PAYTM/...
        - CMS/428910293812/DONATION/...
        - UPI-428910293812-RAISE INDIA...
        - NEFT/428910293812/...
        """
        if not narration:
            return None
            
        patterns = [
            r'(?:UPI|CMS|NEFT|IMPS|RTGS)[/-]([0-9]{12})\b',
            r'(?:AUTO[\s\-_]*ID|AOTID|APP\s*ORDER|ORDER)[/-]([A-Za-z0-9]{8,24})\b',
            r'(?:UTR|REF|TXN|AUTO[\s\-_]*ID|AOTID|ORDER)[:\s/-]*([A-Za-z0-9]{8,24})\b',
            r'\b([0-9]{12})\b'
        ]

        for p in patterns:
            match = re.search(p, str(narration), re.IGNORECASE)
            if match:
                val = match.group(1)
                # Ignore dummy all zeros
                if not val.startswith("000000000000"):
                    return val
        return None

    @classmethod
    def parse_bank_statement_file(cls, file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
        """
        Parses Excel (.xlsx, .xls) or CSV bank statement file.
        Auto-detects Date, Narration, Credit Amount, Balance columns.
        """
        filename_lower = filename.lower()
        if filename_lower.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))

        # Normalize column names for detection
        col_mapping = {}
        for col in df.columns:
            c_norm = str(col).strip().lower().replace("_", " ")
            if any(k in c_norm for k in ["txn date", "transaction date", "value date", "posting date", "date"]):
                if "date" not in col_mapping:
                    col_mapping["date"] = col
            elif any(k in c_norm for k in ["narration", "description", "particulars", "remarks", "details", "transaction details"]):
                if "narration" not in col_mapping:
                    col_mapping["narration"] = col
            elif any(k in c_norm for k in ["credit", "cr", "deposit", "deposit amount", "credit amount", "received"]):
                if "credit" not in col_mapping:
                    col_mapping["credit"] = col
            elif any(k in c_norm for k in ["balance", "closing balance", "bal"]):
                if "balance" not in col_mapping:
                    col_mapping["balance"] = col

        if "narration" not in col_mapping or "credit" not in col_mapping:
            # Fallback heuristic: Try matching by positional columns if header missing or non-standard
            cols = list(df.columns)
            if len(cols) >= 3:
                # Guess date col 0, narration col 1, credit col 2
                col_mapping.setdefault("date", cols[0])
                col_mapping.setdefault("narration", cols[1])
                col_mapping.setdefault("credit", cols[2])
            else:
                raise ValueError("Could not detect Narration and Credit columns in the uploaded bank statement.")

        entries = []
        for _, row in df.iterrows():
            credit_raw = row.get(col_mapping["credit"])
            if pd.isna(credit_raw):
                continue
            
            # Clean credit amount
            credit_str = str(credit_raw).replace(",", "").replace("₹", "").strip()
            try:
                credit_amt = Decimal(credit_str)
                if credit_amt <= 0:
                    continue
            except Exception:
                continue

            narration_val = str(row.get(col_mapping["narration"], "")).strip()
            if not narration_val or narration_val.lower() == "nan":
                continue

            # Parse date
            date_val = None
            if "date" in col_mapping:
                raw_d = row.get(col_mapping["date"])
                try:
                    if pd.notna(raw_d):
                        if isinstance(raw_d, (datetime, pd.Timestamp)):
                            date_val = raw_d.date()
                        else:
                            date_val = pd.to_datetime(raw_d).date()
                except Exception:
                    date_val = date.today()
            if not date_val:
                date_val = date.today()

            # Parse balance
            bal_amt = None
            if "balance" in col_mapping:
                bal_raw = row.get(col_mapping["balance"])
                if pd.notna(bal_raw):
                    try:
                        bal_amt = Decimal(str(bal_raw).replace(",", "").strip())
                    except Exception:
                        bal_amt = None

            # Extract UTR from narration or dedicated columns or row
            utr = cls.extract_utr_from_narration(narration_val)
            if not utr:
                # Check other cells in the row for 12-digit UTR
                for cell in row.values:
                    if pd.notna(cell):
                        m = re.search(r'\b([0-9]{12})\b', str(cell))
                        if m and not m.group(1).startswith("000000000000"):
                            utr = m.group(1)
                            break

            entries.append({
                "transaction_date": date_val,
                "narration": narration_val,
                "credit_amount": credit_amt,
                "balance": bal_amt,
                "extracted_utr": utr
            })

        return entries

    @classmethod
    def run_reconciliation(cls, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Runs automated reconciliation between donations and bank statements.
        
        1. Duplicate UTR check:
           Flags donations with identical UTRs.
           
        2. Exact Match (🟢 Verified):
           statement.extracted_utr == donation.extracted_utr AND statement.credit_amount == donation.extracted_amount
           -> donation.status = MATCHED, is_verified = True, statement.is_reconciled = True
           
        3. Fuzzy Match (🟡 Review Needed):
           Amount matches AND (date within +/- 2 days OR Levenshtein distance <= 2 on UTR)
           -> donation.status = FLAGGED_REVIEW
           
        4. Unmatched:
           Remains FLAGGED_REVIEW / EXTRACTED.
        """
        session_to_close = None
        if db is None:
            db = SessionLocal()
            session_to_close = db

        stats = {
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "duplicates_flagged": 0,
            "total_processed": 0
        }

        try:
            # Step 1: Detect duplicate UTRs in donations
            all_donations = db.query(Donation).all()
            utr_counts: Dict[str, List[Donation]] = {}
            for d in all_donations:
                if d.extracted_utr:
                    utr_counts.setdefault(d.extracted_utr, []).append(d)

            for utr, group in utr_counts.items():
                if len(group) > 1:
                    for d in group:
                        if d.status != DonationStatus.REJECTED:
                            d.status = DonationStatus.FLAGGED_REVIEW
                            d.flagged_reason = f"Duplicate UTR detected: {utr} submitted across multiple donations."
                            stats["duplicates_flagged"] += 1

            # Fetch pending or extracted or flagged donations that are not yet verified
            unverified_donations = db.query(Donation).filter(
                Donation.is_verified == False,
                Donation.status != DonationStatus.REJECTED
            ).all()

            unreconciled_statements = db.query(BankStatementEntry).filter(
                BankStatementEntry.is_reconciled == False
            ).all()

            # Build index of statements by UTR
            statement_by_utr: Dict[str, BankStatementEntry] = {}
            for st in unreconciled_statements:
                if st.extracted_utr:
                    statement_by_utr[st.extracted_utr] = st

            for donation in unverified_donations:
                stats["total_processed"] += 1
                matched = False

                # --- Check Exact Match ---
                if donation.extracted_utr and donation.extracted_utr in statement_by_utr:
                    st = statement_by_utr[donation.extracted_utr]
                    # Check amount match (tolerance 0.00)
                    if donation.extracted_amount is not None and abs(Decimal(str(donation.extracted_amount)) - Decimal(str(st.credit_amount))) < Decimal("0.01"):
                        donation.matched_statement_id = st.id
                        
                        if donation.is_flagged_fraud:
                            # Fraud-flagged donations require human CA audit before verification
                            donation.status = DonationStatus.FLAGGED_REVIEW
                            donation.flagged_reason = f"Exact bank credit matched (₹{st.credit_amount}), but submission is FLAGGED FOR FRAUD review: {', '.join(donation.fraud_reasons or [])}"
                            donation.bank_matched_mode = "AUTO_FUZZY"
                        else:
                            donation.status = DonationStatus.MATCHED
                            donation.is_verified = True
                            donation.flagged_reason = None
                            donation.bank_matched_mode = "AUTO_EXACT"
                            donation.verified_at = datetime.now(timezone.utc)
                            donation.verified_by_user = "AUTO_RECON_ENGINE"
                            donation.admin_audit_notes = "Auto-reconciled: Exact match on 12-digit UTR and credit amount"
                            st.is_reconciled = True
                            stats["exact_matches"] += 1
                            # Remove from pool
                            del statement_by_utr[donation.extracted_utr]
                        matched = True

                if matched:
                    continue

                # --- Check Fuzzy Match ---
                best_candidate = None
                best_score = 0.0
                best_reason = ""

                for st in unreconciled_statements:
                    if st.is_reconciled:
                        continue

                    amount_matches = False
                    if donation.extracted_amount is not None:
                        amount_matches = (abs(Decimal(str(donation.extracted_amount)) - Decimal(str(st.credit_amount))) < Decimal("0.01"))

                    # Check UTR Levenshtein
                    dist = 999
                    if donation.extracted_utr and st.extracted_utr:
                        dist = levenshtein_distance(donation.extracted_utr, st.extracted_utr)

                    # Check date difference
                    days_diff = 999
                    if donation.extracted_date and st.transaction_date:
                        donation_dt = donation.extracted_date.date() if isinstance(donation.extracted_date, datetime) else donation.extracted_date
                        days_diff = abs((donation_dt - st.transaction_date).days)

                    if amount_matches and dist <= 2:
                        score = 0.95 - (dist * 0.1)
                        if score > best_score:
                            best_score = score
                            best_candidate = st
                            best_reason = f"Fuzzy UTR match (distance {dist}): Extracted {donation.extracted_utr} vs Bank {st.extracted_utr}. Amount ₹{st.credit_amount} matches exactly."
                    elif amount_matches and days_diff <= 2:
                        score = 0.80 - (days_diff * 0.05)
                        if score > best_score:
                            best_score = score
                            best_candidate = st
                            best_reason = f"Amount matches ₹{st.credit_amount} within {days_diff} day(s), but UTR differs or missing in OCR. Needs manual verification."

                if best_candidate and best_score >= 0.70:
                    donation.status = DonationStatus.FLAGGED_REVIEW
                    donation.matched_statement_id = best_candidate.id
                    donation.flagged_reason = best_reason
                    stats["fuzzy_matches"] += 1

            db.commit()
            return stats
        except Exception as e:
            db.rollback()
            logger.error(f"Error during reconciliation run: {e}")
            raise
        finally:
            if session_to_close is not None:
                session_to_close.close()

    @classmethod
    def get_fuzzy_candidates(cls, db: Session, donation: Donation) -> List[Dict[str, Any]]:
        """
        Returns ranked candidate bank statement entries for manual review on the admin split-screen.
        """
        unreconciled_statements = db.query(BankStatementEntry).filter(
            BankStatementEntry.is_reconciled == False
        ).all()

        candidates = []
        for st in unreconciled_statements:
            amount_diff = Decimal("999999")
            if donation.extracted_amount is not None:
                amount_diff = abs(Decimal(str(donation.extracted_amount)) - Decimal(str(st.credit_amount)))

            dist = 999
            if donation.extracted_utr and st.extracted_utr:
                dist = levenshtein_distance(donation.extracted_utr, st.extracted_utr)

            days_diff = 999
            if donation.extracted_date and st.transaction_date:
                donation_dt = donation.extracted_date.date() if isinstance(donation.extracted_date, datetime) else donation.extracted_date
                days_diff = abs((donation_dt - st.transaction_date).days)

            # Compute match score
            score = 0.0
            match_type = "UNMATCHED"
            if dist == 0 and amount_diff == Decimal("0"):
                score = 1.0
                match_type = "EXACT"
            elif dist <= 2 and amount_diff == Decimal("0"):
                score = 0.9 - (dist * 0.1)
                match_type = "FUZZY_UTR"
            elif amount_diff == Decimal("0") and days_diff <= 3:
                score = 0.75 - (days_diff * 0.05)
                match_type = "AMOUNT_DATE_MATCH"
            elif dist <= 2:
                score = 0.60
                match_type = "SIMILAR_UTR"
            elif amount_diff == Decimal("0"):
                score = 0.50
                match_type = "AMOUNT_MATCH"

            if score > 0.45:
                candidates.append({
                    "statement_entry": to_pydantic(BankStatementEntryResponse, st),
                    "utr_distance": dist if dist < 999 else -1,
                    "amount_diff": amount_diff,
                    "days_diff": days_diff if days_diff < 999 else -1,
                    "confidence_score": round(score, 2),
                    "match_type": match_type
                })

        candidates.sort(key=lambda x: x["confidence_score"], reverse=True)
        return candidates[:10]
