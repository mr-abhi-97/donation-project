"""
Raise India Foundation - Programmatic Ledger Purge, Reset & Reprocessing Engine
================================================================================
Database Management Utility for SQLAlchemy & SQLite/PostgreSQL.

Modes:
  1. --mode purge       : Removes all failed, mock, and invalid records (status = 'REJECTED' or utr IS NULL).
  2. --mode reset-all   : Completely wipes all donation records to achieve a pristine 0-row state on http://localhost:3000.
  3. --mode reprocess   : Scans all existing screenshot files on disk, executes the active RapidOCR/Tesseract engine,
                          extracts real 12-digit UTRs and amounts, and upgrades records to EXTRACTED / MATCHED.
  4. --mode status      : Displays complete ledger telemetry and status breakdown without modifying data.

Usage:
  python reset_ledger.py --mode purge
  python reset_ledger.py --mode reset-all
  python reset_ledger.py --mode reprocess
  python reset_ledger.py --mode status
"""

import os
import sys
import argparse
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import settings
from backend.app.database import SessionLocal, engine
from backend.app.models import Donation, Donor, BankStatementEntry, TaxReceipt80G, DonationStatus
from backend.app.services.ocr import OCRService


# Ensure UTF-8 output on Windows CP1252 consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def print_banner():
    print("=" * 70)
    print(" [Raise India Foundation] Database Ledger Purge & Reset Utility")
    print("=" * 70)


def get_ledger_status(db):
    """Returns a dictionary summary of all records currently in the database."""
    total = db.query(Donation).count()
    rejected = db.query(Donation).filter(Donation.status == DonationStatus.REJECTED).count()
    extracted = db.query(Donation).filter(Donation.status == DonationStatus.EXTRACTED).count()
    matched = db.query(Donation).filter(Donation.status == DonationStatus.MATCHED).count()
    flagged = db.query(Donation).filter(Donation.status == DonationStatus.FLAGGED_REVIEW).count()
    dup = db.query(Donation).filter(Donation.status == DonationStatus.DUPLICATE_FLAGGED).count()
    donors_count = db.query(Donor).count()
    stmts_count = db.query(BankStatementEntry).count()

    return {
        "total_donations": total,
        "rejected": rejected,
        "extracted": extracted,
        "matched": matched,
        "flagged_review": flagged,
        "duplicate_flagged": dup,
        "total_donors": donors_count,
        "bank_statement_entries": stmts_count,
    }


def display_status(db):
    stats = get_ledger_status(db)
    print("\nCURRENT DATABASE LEDGER AUDIT:")
    print("-" * 50)
    print(f" Total Donation Records    : {stats['total_donations']}")
    print(f"  |-- REJECTED (Failed/Mock): {stats['rejected']}")
    print(f"  |-- EXTRACTED (Valid OCR) : {stats['extracted']}")
    print(f"  |-- MATCHED (Reconciled)  : {stats['matched']}")
    print(f"  |-- FLAGGED_REVIEW        : {stats['flagged_review']}")
    print(f"  \\-- DUPLICATE_FLAGGED     : {stats['duplicate_flagged']}")
    print(f" Total Donors Registered   : {stats['total_donors']}")
    print(f" Bank Statement Entries    : {stats['bank_statement_entries']}")
    print("-" * 50)


def purge_rejected(db):
    """
    Deletes all records where status is REJECTED or extracted_utr is NULL.
    Also cleans up associated orphaned donors.
    """
    print("\n[+] Initiating PURGE operation for REJECTED and incomplete records...")
    try:
        # Find all target donations
        targets = db.query(Donation).filter(
            (Donation.status == DonationStatus.REJECTED) |
            (Donation.extracted_utr == None) |
            (Donation.extracted_utr == "")
        ).all()

        target_count = len(targets)
        if target_count == 0:
            print(" -> No REJECTED or empty UTR records found. Ledger is already clean.")
            return 0

        donor_ids_to_check = set()
        for d in targets:
            if d.donor_id:
                donor_ids_to_check.add(d.donor_id)
            # Delete associated tax receipt if any
            if d.tax_receipt:
                db.delete(d.tax_receipt)
            db.delete(d)

        db.flush()

        # Clean orphaned donors created during failed uploads
        orphaned_donors = 0
        for d_id in donor_ids_to_check:
            remaining_donations = db.query(Donation).filter(Donation.donor_id == d_id).count()
            if remaining_donations == 0:
                donor_obj = db.query(Donor).filter(Donor.id == d_id).first()
                if donor_obj:
                    db.delete(donor_obj)
                    orphaned_donors += 1

        db.commit()
        print(f" [SUCCESS] Purged {target_count} REJECTED donation(s) and {orphaned_donors} orphaned donor record(s).")
        return target_count

    except Exception as e:
        db.rollback()
        print(f" [ERROR] Purge failed! Rolled back transaction cleanly. Reason: {e}")
        raise


def reset_all_donations(db, include_statements=False):
    """
    Wipes all donation records to achieve a pristine 0-row state.
    """
    print("\n[+] Initiating RESET-ALL operation (Wiping all donations)...")
    try:
        # 1. Delete all tax receipts
        receipts_deleted = db.query(TaxReceipt80G).delete()

        # 2. Delete all donations
        donations_deleted = db.query(Donation).delete()

        # 3. Clean up donors
        donors_deleted = db.query(Donor).delete()

        # 4. Optional bank statement reset
        statements_deleted = 0
        if include_statements:
            statements_deleted = db.query(BankStatementEntry).delete()
        else:
            # Unmark reconciled flag on statements
            db.query(BankStatementEntry).update({"is_reconciled": False})

        db.commit()
        print(f" [SUCCESS] Reset complete:")
        print(f"  - Deleted {donations_deleted} donation records.")
        print(f"  - Deleted {receipts_deleted} tax receipts.")
        print(f"  - Deleted {donors_deleted} donor records.")
        if include_statements:
            print(f"  - Deleted {statements_deleted} bank statement records.")
        else:
            print(f"  - Preserved bank statements with reconciled state reset to False.")
        return donations_deleted

    except Exception as e:
        db.rollback()
        print(f" [ERROR] Reset-all failed! Rolled back transaction cleanly. Reason: {e}")
        raise


def reprocess_existing_records(db):
    """
    Scans existing donation records, re-runs active OCR (RapidOCR/Tesseract) on their screenshots,
    extracts real 12-digit UTRs and actual amounts, and upgrades records from REJECTED to EXTRACTED/MATCHED.
    """
    print("\n[+] Initiating REPROCESS operation on saved screenshots...")
    donations = db.query(Donation).all()
    if not donations:
        print(" -> No donation records found to reprocess.")
        return 0

    reprocessed_success = 0
    reprocessed_failed = 0

    try:
        for idx, d in enumerate(donations, 1):
            if not d.screenshot_url:
                continue

            # Resolve screenshot absolute path on filesystem
            raw_url = d.screenshot_url.lstrip("/")
            if raw_url.startswith("uploads/"):
                raw_url = raw_url[len("uploads/"):]
            
            # Primary screenshot directory check
            screenshot_path = settings.SCREENSHOTS_DIR / Path(raw_url).name
            if not screenshot_path.exists():
                screenshot_path = settings.BASE_DIR / "uploads" / raw_url

            if not screenshot_path.exists():
                print(f" [{idx}/{len(donations)}] Warning: Screenshot not found on disk: {d.screenshot_url}")
                reprocessed_failed += 1
                continue

            # Run active OCR Engine
            ocr_res = OCRService.process_screenshot(str(screenshot_path), screenshot_path.name)
            is_valid = ocr_res.get("is_valid_receipt", False)
            extracted_utr = ocr_res.get("extracted_utr")
            extracted_amt = ocr_res.get("extracted_amount")
            extracted_name = ocr_res.get("extracted_donor_name")

            if is_valid and (extracted_utr or extracted_amt):
                d.extracted_utr = extracted_utr
                d.extracted_amount = Decimal(str(extracted_amt)) if extracted_amt else d.extracted_amount
                d.status = DonationStatus.EXTRACTED
                d.is_verified = False
                d.is_flagged_fraud = False
                d.flagged_reason = None
                d.ocr_confidence = ocr_res.get("confidence", 0.95)
                d.raw_ocr_payload = ocr_res

                if ocr_res.get("extracted_date"):
                    try:
                        d.extracted_date = datetime.fromisoformat(ocr_res["extracted_date"])
                    except Exception:
                        pass

                # Update donor name if present
                if extracted_name and extracted_name != "Unverified Donor" and d.donor:
                    d.donor.full_name = extracted_name

                # Auto-check if matches an existing bank statement
                if extracted_utr:
                    matching_stmt = db.query(BankStatementEntry).filter(
                        BankStatementEntry.extracted_utr == extracted_utr
                    ).first()
                    if matching_stmt:
                        d.matched_statement_id = matching_stmt.id
                        d.status = DonationStatus.MATCHED
                        d.is_verified = True
                        matching_stmt.is_reconciled = True

                reprocessed_success += 1
                print(f" [{idx}/{len(donations)}] REPROCESSED: UTR={extracted_utr} | Amt=Rs.{extracted_amt} | Status={d.status}")
            else:
                d.status = DonationStatus.REJECTED
                d.flagged_reason = ocr_res.get("domain_rejection_reason") or "NON_PAYMENT_IMAGE: Missing UPI payment anchors."
                reprocessed_failed += 1
                print(f" [{idx}/{len(donations)}] NON-PAYMENT: {screenshot_path.name} marked REJECTED.")

        db.commit()
        print(f"\n [SUCCESS] Reprocess complete:")
        print(f"  - Successfully updated: {reprocessed_success} record(s)")
        print(f"  - Rejected non-payment: {reprocessed_failed} record(s)")
        return reprocessed_success

    except Exception as e:
        db.rollback()
        print(f" [ERROR] Reprocess failed! Rolled back transaction cleanly. Reason: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Raise India - Ledger Database Reset & Reprocessing Tool")
    parser.add_argument(
        "--mode",
        choices=["purge", "reset-all", "reprocess", "status"],
        default="status",
        help="Operation to perform: 'purge' (delete REJECTED), 'reset-all' (wipe to 0 rows), 'reprocess' (re-OCR), or 'status'"
    )
    parser.add_argument(
        "--include-statements",
        action="store_true",
        help="When resetting all, also deletes bank statement entries (default: false)"
    )

    args = parser.parse_args()

    print_banner()
    db = SessionLocal()

    try:
        if args.mode == "status":
            display_status(db)
            print("\nRecommended Next Steps:")
            print(" - To purge failed/rejected mock uploads: python reset_ledger.py --mode purge")
            print(" - To reset the entire ledger to 0 rows : python reset_ledger.py --mode reset-all")
            print(" - To re-run OCR on existing screenshots: python reset_ledger.py --mode reprocess")

        elif args.mode == "purge":
            display_status(db)
            purge_rejected(db)
            display_status(db)

        elif args.mode == "reset-all":
            display_status(db)
            reset_all_donations(db, include_statements=args.include_statements)
            display_status(db)

        elif args.mode == "reprocess":
            display_status(db)
            reprocess_existing_records(db)
            display_status(db)

    finally:
        db.close()


if __name__ == "__main__":
    main()
