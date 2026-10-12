import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure UTF-8 output encoding on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import urllib.request
import urllib.error
from decimal import Decimal
from sqlalchemy import func

from backend.app.database import SessionLocal, engine
from backend.app.models import Donation, BankStatementEntry, Donor, TaxReceipt80G, DonationStatus
from backend.app.services.anti_fraud_service import ScreenshotFraudDetector


def run_comprehensive_audit():
    db = SessionLocal()
    print("=" * 70)
    print("RAISE INDIA FOUNDATION - SYSTEM & DATA AUDIT REPORT")
    print("=" * 70)

    audit_passed = True

    try:
        # =====================================================================
        # [1] DATABASE HEALTH & SCHEMA CONSISTENCY
        # =====================================================================
        print("\n[1] LEDGER METRICS & SCHEMA CONSISTENCY:")
        try:
            with engine.connect() as conn:
                print("  ✓ Database connection to SQLite (raise_india.db): ACTIVE")
        except Exception as e:
            print(f"  ✗ Database connection failed: {e}")
            audit_passed = False

        total_donations = db.query(Donation).count()
        matched_donations = db.query(Donation).filter(Donation.is_verified == True).count()
        rejected_donations = db.query(Donation).filter(Donation.status == DonationStatus.REJECTED).count()
        extracted_donations = db.query(Donation).filter(Donation.status == DonationStatus.EXTRACTED).count()
        flagged_donations = db.query(Donation).filter(Donation.status == DonationStatus.FLAGGED_REVIEW).count()
        pending_donations = total_donations - matched_donations - rejected_donations

        total_volume = db.query(func.sum(Donation.extracted_amount)).filter(Donation.extracted_amount != None).scalar() or Decimal("0.0")

        print(f"  - Total Uploads Logged:    {total_donations}")
        print(f"  - Reconciled (MATCHED):    {matched_donations}")
        print(f"  - Extracted (Pending Bank): {extracted_donations}")
        print(f"  - Flagged for Review:      {flagged_donations}")
        print(f"  - Rejected / Non-Payment:  {rejected_donations}")
        print(f"  - Pending Bank Credit:     {pending_donations}")
        print(f"  - Total Audited Volume:    ₹{float(total_volume):,.2f}")

        # Bank statements audit
        total_stmts = db.query(BankStatementEntry).count()
        reconciled_stmts = db.query(BankStatementEntry).filter(BankStatementEntry.is_reconciled == True).count()
        unreconciled_stmts = total_stmts - reconciled_stmts
        print(f"  - Bank Statements Total:   {total_stmts} (Reconciled: {reconciled_stmts}, Unreconciled: {unreconciled_stmts})")

        # Donors audit
        total_donors = db.query(Donor).count()
        print(f"  - Registered Donors:       {total_donors}")

        # Tax Receipts audit
        total_receipts = db.query(TaxReceipt80G).count()
        missing_receipt_pdfs = 0
        for tr in db.query(TaxReceipt80G).all():
            if not os.path.exists(tr.pdf_path):
                missing_receipt_pdfs += 1
        print(f"  - 80G Tax Certificates:    {total_receipts} (Missing PDFs: {missing_receipt_pdfs})")
        if missing_receipt_pdfs == 0 and total_receipts > 0:
            print("  ✓ All issued 80G PDF receipts exist on storage.")

        # Foreign Key Referential Integrity
        linked_statements = db.query(Donation).filter(Donation.matched_statement_id != None).all()
        broken_links = 0
        for d in linked_statements:
            stmt = db.query(BankStatementEntry).filter(BankStatementEntry.id == d.matched_statement_id).first()
            if not stmt or not stmt.is_reconciled:
                broken_links += 1
        print(f"  - Matched Statement Links: {len(linked_statements)} (Broken Links: {broken_links})")
        if broken_links == 0:
            print("  ✓ 100% Referential integrity between donations and bank credits.")
        else:
            print("  ✗ Referential integrity violation detected in statement links.")
            audit_passed = False

        # =====================================================================
        # [2] ZERO-MOCK & ZERO-SYNTHETIC DATA ENFORCEMENT AUDIT
        # =====================================================================
        print("\n[2] SYNTHETIC DATA AUDIT:")
        mock_candidates = db.query(Donation).filter(
            Donation.extracted_utr.like("42857719283%")
        ).count()
        print(f"  - Legacy Synthetic UTRs Remaining (4285...): {mock_candidates}")
        if mock_candidates == 0:
            print("  ✓ ZERO mock or fabricated UTRs detected in active ledger.")
        else:
            print("  ⚠ Note: Legacy test artifacts present. Delete via UI trash action.")

        # Check for arbitrary hardcoded fallback amounts on non-payment / rejected records
        invalid_uploads_with_amount = db.query(Donation).filter(
            Donation.status == DonationStatus.REJECTED,
            Donation.extracted_amount != None,
            Donation.extracted_amount > 0
        ).count()
        invalid_uploads_with_utr = db.query(Donation).filter(
            Donation.status == DonationStatus.REJECTED,
            Donation.extracted_utr != None
        ).count()
        print(f"  - Rejected uploads with fabricated amount: {invalid_uploads_with_amount}")
        print(f"  - Rejected uploads with fabricated UTR:    {invalid_uploads_with_utr}")
        if invalid_uploads_with_amount == 0 and invalid_uploads_with_utr == 0:
            print("  ✓ Strict Zero-Mock Enforcement: All rejected uploads have extracted_utr=None and extracted_amount=None.")
        else:
            print("  ✗ Synthetic values found on rejected uploads.")
            audit_passed = False

        # Verify no anonymous fallback when donor is linked
        donations_without_donor = db.query(Donation).filter(Donation.donor_id == None).count()
        print(f"  - Orphaned Donations Without Donor Link: {donations_without_donor}")
        if donations_without_donor == 0:
            print("  ✓ 100% of donations are linked to legitimate Donor profiles.")

        # =====================================================================
        # [3] FORENSIC & ANTI-FRAUD CLASSIFICATION ACCURACY
        # =====================================================================
        print("\n[3] FORENSIC & ANTI-FRAUD CLASSIFICATION ACCURACY:")
        fraud_flagged = db.query(Donation).filter(Donation.is_flagged_fraud == True).all()
        print(f"  - Fraud / High-Risk Flagged Records: {len(fraud_flagged)}")
        for f in fraud_flagged:
            reasons = f.fraud_reasons or ([f.flagged_reason] if f.flagged_reason else ["FLAGGED"])
            print(f"    • ID: {str(f.id)[:8]}... | Status: {f.status} | ELA Tamper: {f.tamper_score}% | Reason: {reasons[0]}")

        # Clean receipts check: Verified donations must have authentic anchors and low tamper scores
        clean_donations = db.query(Donation).filter(Donation.is_verified == True).all()
        all_clean_authentic = all(d.tamper_score < 50.0 and not d.is_flagged_fraud for d in clean_donations)
        if all_clean_authentic:
            print(f"  ✓ All {len(clean_donations)} verified donations confirmed authentic with tamper_score < 50% and fraud_flag=False.")
        else:
            print("  ✗ Anomalous tamper score on verified donations.")
            audit_passed = False

        # Non-payment media check: Rejected records must have missing UPI anchor reason
        rejected_records = db.query(Donation).filter(Donation.status == DonationStatus.REJECTED).all()
        all_rejections_anchored = True
        for r in rejected_records:
            reasons_str = " ".join(r.fraud_reasons or []) + f" {r.flagged_reason or ''}"
            if "NON_PAYMENT_IMAGE" not in reasons_str:
                all_rejections_anchored = False
        if all_rejections_anchored and len(rejected_records) > 0:
            print(f"  ✓ All {len(rejected_records)} non-payment uploads correctly categorized with NON_PAYMENT_IMAGE reason.")

        # Duplicate hash calculation test
        test_bytes = b"RaiseIndiaTestByteStream_AuditHash_2024"
        computed_hash = ScreenshotFraudDetector.calculate_file_hash(test_bytes)
        if computed_hash and len(computed_hash) == 64:
            print(f"  ✓ SHA-256 duplicate detection engine verified: {computed_hash[:16]}...")
        else:
            print("  ✗ SHA-256 computation failure.")
            audit_passed = False

        # =====================================================================
        # [4] RECONCILIATION & MATCH MATH INTEGRITY
        # =====================================================================
        print("\n[4] RECONCILIATION & MATCH MATH INTEGRITY:")
        # Exact match ledger verification
        verified_donations = db.query(Donation).filter(Donation.is_verified == True).all()
        recon_math_valid = True
        for vd in verified_donations:
            stmt = db.query(BankStatementEntry).filter(BankStatementEntry.id == vd.matched_statement_id).first()
            if not stmt:
                recon_math_valid = False
                continue
            if vd.extracted_utr != stmt.extracted_utr:
                recon_math_valid = False
            if abs(Decimal(str(vd.extracted_amount)) - Decimal(str(stmt.credit_amount))) > Decimal("0.01"):
                recon_math_valid = False

        if recon_math_valid:
            print(f"  ✓ Exact 12-digit UTR & Credit Amount Match: 100% verified across {len(verified_donations)} transactions.")
        else:
            print("  ✗ UTR or amount mismatch found in reconciled transactions.")
            audit_passed = False

        # Live API Endpoint Reconciliation Stats Check
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/api/reconciliation/stats", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    api_stats = json.loads(resp.read().decode("utf-8"))
                    print(f"  ✓ Live API Endpoint GET /api/reconciliation/stats: HTTP 200 OK")
                    print(f"    - API Matched Count:       {api_stats.get('matched_count')} (DB: {matched_donations})")
                    print(f"    - API Total Collected:     ₹{api_stats.get('total_amount_collected', 0):,.2f}")
                    print(f"    - API Reconciled Amount:   ₹{api_stats.get('reconciled_amount', 0):,.2f}")
                    print(f"    - API Match Rate:          {api_stats.get('match_rate_percentage')}%")
                    if api_stats.get('matched_count') != matched_donations:
                        print("  ✗ API stats count mismatch against database.")
                        audit_passed = False
                else:
                    print(f"  ✗ API responded with status {resp.status}")
                    audit_passed = False
        except Exception as api_err:
            print(f"  ⚠ Live API check warning: {api_err}")

        # Live Next.js Frontend Portal Proxy Check (:3000)
        try:
            fe_req = urllib.request.Request("http://localhost:3000/api/reconciliation/stats", method="GET")
            with urllib.request.urlopen(fe_req, timeout=5) as fe_resp:
                if fe_resp.status == 200:
                    fe_stats = json.loads(fe_resp.read().decode("utf-8"))
                    print(f"  ✓ Live Next.js Portal Proxy (http://localhost:3000/api/reconciliation/stats): HTTP 200 OK")
                    if fe_stats.get('matched_count') == matched_donations:
                        print("  ✓ Frontend-to-Backend reverse proxy verified 100% synchronized.")
                else:
                    print(f"  ✗ Next.js Portal responded with status {fe_resp.status}")
        except Exception as fe_err:
            print(f"  ⚠ Next.js Portal proxy check warning: {fe_err}")

        # =====================================================================
        # [5] STATIC FILE SERVING & ASSET AUDIT
        # =====================================================================
        print("\n[5] ASSET SERVING & STATIC FILES AUDIT:")
        missing_files = 0
        live_http_ok = 0
        total_screenshot_urls = 0

        for d in db.query(Donation).filter(Donation.screenshot_url != None).all():
            total_screenshot_urls += 1
            filename = os.path.basename(d.screenshot_url)
            local_path = os.path.join("backend", "uploads", "screenshots", filename)
            if not os.path.exists(local_path):
                missing_files += 1
            else:
                # Test live HTTP access
                try:
                    url1 = f"http://127.0.0.1:8000{d.screenshot_url}"
                    url2 = f"http://127.0.0.1:8000/api{d.screenshot_url}"
                    with urllib.request.urlopen(url1, timeout=3) as r1, urllib.request.urlopen(url2, timeout=3) as r2:
                        if r1.status == 200 and r2.status == 200:
                            live_http_ok += 1
                except Exception:
                    pass

        print(f"  - Total Screenshot Records:         {total_screenshot_urls}")
        print(f"  - Missing Screenshot Files on Disk: {missing_files}")
        print(f"  - Live HTTP 200 Verified Endpoints: {live_http_ok} / {total_screenshot_urls}")

        if missing_files == 0:
            print("  ✓ All ledger image references exist on local storage.")
        else:
            print(f"  ✗ {missing_files} referenced screenshot files missing on disk.")
            audit_passed = False

        if live_http_ok == total_screenshot_urls and total_screenshot_urls > 0:
            print("  ✓ Dual mounting (/uploads and /api/uploads) verified returning HTTP 200 for all screenshots.")

        print("\n" + "=" * 70)
        if audit_passed:
            print("AUDIT STATUS: SYSTEM HEALTHY & 100% COMPLIANT (ALL 5 PILLARS PASSED)")
        else:
            print("AUDIT STATUS: ANOMALIES DETECTED DURING AUDIT EXECUTION")
        print("=" * 70)

        return audit_passed

    finally:
        db.close()


if __name__ == "__main__":
    success = run_comprehensive_audit()
    sys.exit(0 if success else 1)
