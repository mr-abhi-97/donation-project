import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.database import get_db
from backend.app.models import Donation, BankStatementEntry, DonationStatus, TaxReceipt80G
from backend.app.schemas import (
    ReconciliationStatsResponse, FuzzyCandidateResponse, DonationResponse
)
from backend.app.services.reconciliation_service import ReconciliationService
from backend.app.services.receipt_service import ReceiptService
from backend.app.services.notification_service import NotificationService
from backend.app.config import settings

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@router.get("/stats", response_model=ReconciliationStatsResponse)
def get_reconciliation_stats(db: Session = Depends(get_db)):
    """
    Computes real-time statistics for the reconciliation dashboard including fraud counts.
    """
    total_donations = db.query(Donation).count()
    matched_count = db.query(Donation).filter(Donation.status == DonationStatus.MATCHED).count()
    pending_count = db.query(Donation).filter(
        (Donation.status == DonationStatus.PENDING_OCR) | 
        (Donation.status == DonationStatus.EXTRACTED) |
        (Donation.status == DonationStatus.PENDING)
    ).count()
    flagged_count = db.query(Donation).filter(Donation.status == DonationStatus.FLAGGED_REVIEW).count()
    rejected_count = db.query(Donation).filter(Donation.status == DonationStatus.REJECTED).count()
    fraud_flagged_count = db.query(Donation).filter(Donation.is_flagged_fraud == True).count()

    total_amount_sum = db.query(func.sum(Donation.extracted_amount)).scalar() or Decimal("0.0")
    
    reconciled_amount_sum = db.query(func.sum(Donation.extracted_amount)).filter(
        Donation.is_verified == True
    ).scalar() or Decimal("0.0")

    total_statement_entries = db.query(BankStatementEntry).count()
    unreconciled_statement_count = db.query(BankStatementEntry).filter(
        BankStatementEntry.is_reconciled == False
    ).count()

    match_rate = (matched_count / total_donations * 100.0) if total_donations > 0 else 0.0

    return ReconciliationStatsResponse(
        total_donations=total_donations,
        matched_count=matched_count,
        pending_count=pending_count,
        flagged_count=flagged_count,
        rejected_count=rejected_count,
        total_amount_collected=total_amount_sum,
        reconciled_amount=reconciled_amount_sum,
        match_rate_percentage=round(match_rate, 1),
        total_statement_entries=total_statement_entries,
        unreconciled_statement_count=unreconciled_statement_count,
        fraud_flagged_count=fraud_flagged_count
    )


@router.post("/run", response_model=Dict[str, Any])
def trigger_reconciliation(db: Session = Depends(get_db)):
    """
    Runs automated reconciliation algorithm across all pending/unverified donations and statement entries.
    """
    results = ReconciliationService.run_reconciliation(db)
    return {
        "status": "completed",
        "details": results
    }


@router.get("/candidates/{donation_id}", response_model=List[FuzzyCandidateResponse])
def get_candidates_for_donation(donation_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Returns ranked fuzzy match candidates for a donation on the split-screen view.
    """
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    candidates = ReconciliationService.get_fuzzy_candidates(db, donation)
    return candidates


@router.post("/manual-link", response_model=DonationResponse)
def manual_link_and_verify(
    background_tasks: BackgroundTasks,
    donation_id: uuid.UUID = Query(...),
    statement_id: uuid.UUID = Query(...),
    verified_by_user: Optional[str] = Query("Admin / CA Auditor"),
    admin_audit_notes: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Admin manually associates a donation with a bank statement entry and verifies it.
    Enforces double issuance check, logs CA Audit trail, generates 80G receipt, and dispatches via WhatsApp.
    """
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    statement = db.query(BankStatementEntry).filter(BankStatementEntry.id == statement_id).first()
    if not statement:
        raise HTTPException(status_code=404, detail="Bank statement entry not found")

    target_utr = donation.extracted_utr or statement.extracted_utr

    # Double issuance check
    if target_utr:
        dup = db.query(Donation).filter(
            Donation.extracted_utr == target_utr,
            Donation.is_verified == True,
            Donation.id != donation.id
        ).first()
        if dup:
            raise HTTPException(
                status_code=400,
                detail=f"Double issuance blocked: 80G certificate has already been issued for UTR '{target_utr}' on donation {dup.id}."
            )

    # Link and verify
    donation.matched_statement_id = statement.id
    donation.status = DonationStatus.MATCHED
    donation.is_verified = True
    donation.is_flagged_fraud = False
    donation.flagged_reason = None
    statement.is_reconciled = True

    # Audit Trail
    donation.verified_by_user = verified_by_user
    donation.verified_at = datetime.now(timezone.utc)
    donation.bank_matched_mode = "MANUAL_OVERRIDE"
    donation.admin_audit_notes = admin_audit_notes or f"Manually linked to bank narration: {statement.narration[:80]}"

    # Copy fields if missing
    if not donation.extracted_amount and statement.credit_amount:
        donation.extracted_amount = statement.credit_amount

    if not donation.extracted_utr and statement.extracted_utr:
        donation.extracted_utr = statement.extracted_utr

    # Issue 80G Tax Receipt
    if donation.donor and not donation.tax_receipt:
        receipt_count = db.query(TaxReceipt80G).count() + 1
        receipt_no = ReceiptService.generate_receipt_number(receipt_count)
        pdf_path = ReceiptService.generate_80g_pdf(donation, donation.donor, receipt_no)
        pdf_url = f"/api/receipts/download/{receipt_no.replace('/', '_')}.pdf"

        tax_rec = TaxReceipt80G(
            id=uuid.uuid4(),
            donation_id=donation.id,
            receipt_number=receipt_no,
            financial_year=settings.CURRENT_FINANCIAL_YEAR,
            eligible_amount=donation.extracted_amount or statement.credit_amount,
            pdf_path=str(pdf_path),
            pdf_url=pdf_url
        )
        db.add(tax_rec)
        db.flush()

        # WhatsApp dispatch
        if donation.donor.phone:
            background_tasks.add_task(
                NotificationService.send_whatsapp_80g_receipt,
                phone=donation.donor.phone,
                donor_name=donation.donor.full_name,
                receipt_url=pdf_url,
                amount=float(donation.extracted_amount or statement.credit_amount),
                receipt_number=receipt_no
            )

    db.commit()
    db.refresh(donation)
    return donation


@router.post("/unlink/{donation_id}", response_model=DonationResponse)
def unlink_donation(donation_id: uuid.UUID, db: Session = Depends(get_db)):
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    if donation.matched_statement_id:
        st = db.query(BankStatementEntry).filter(BankStatementEntry.id == donation.matched_statement_id).first()
        if st:
            st.is_reconciled = False
        donation.matched_statement_id = None

    donation.is_verified = False
    donation.status = DonationStatus.EXTRACTED
    donation.bank_matched_mode = None
    donation.verified_at = None
    donation.verified_by_user = None
    db.commit()
    db.refresh(donation)
    return donation
