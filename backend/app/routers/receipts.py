import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import TaxReceipt80G, Donation, Donor
from backend.app.schemas import TaxReceiptResponse
from backend.app.services.receipt_service import ReceiptService

router = APIRouter(prefix="/receipts", tags=["Tax Receipts"])


@router.get("/download/{filename}")
def download_receipt_pdf(filename: str):
    """
    Downloads or streams generated 80G PDF receipt.
    """
    file_path = settings.RECEIPTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Receipt PDF file not found")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename
    )


@router.get("/export/form-10bd")
def export_form_10bd(db: Session = Depends(get_db)):
    """
    Exports Form 10BD Excel table for all verified / matched donations in compliant format.
    """
    verified_donations = db.query(Donation).options(
        joinedload(Donation.donor)
    ).filter(
        Donation.is_verified == True
    ).order_by(Donation.created_at.asc()).all()

    if not verified_donations:
        # Also include any matched donations even if not formally marked is_verified
        verified_donations = db.query(Donation).options(
            joinedload(Donation.donor)
        ).filter(
            Donation.donor != None
        ).order_by(Donation.created_at.asc()).all()

    excel_bytes = ReceiptService.export_form_10bd_excel(verified_donations)

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=Form_10BD_Raise_India_{settings.CURRENT_FINANCIAL_YEAR}.xlsx"}
    )


@router.get("/lookup")
def lookup_receipt_for_donor(
    pan: Optional[str] = Query(None, description="Donor PAN Number"),
    tracking_id: Optional[str] = Query(None, description="Donation Tracking ID"),
    db: Session = Depends(get_db)
):
    """
    Public lookup endpoint: Donors can check verification status and download 80G certificate using PAN or Tracking ID.
    """
    query = db.query(Donation).options(
        joinedload(Donation.donor),
        joinedload(Donation.tax_receipt)
    )

    if tracking_id:
        try:
            tid = uuid.UUID(tracking_id.strip())
            donation = query.filter(Donation.id == tid).first()
            if not donation:
                raise HTTPException(status_code=404, detail="No donation found with this Tracking ID")
            return {
                "status": "found",
                "donation_id": donation.id,
                "donor_name": donation.donor.full_name if donation.donor else "Donor",
                "pan_number": donation.donor.pan_number if donation.donor else None,
                "extracted_utr": donation.extracted_utr,
                "amount": float(donation.extracted_amount or 0),
                "donation_status": donation.status,
                "is_verified": donation.is_verified,
                "has_receipt": donation.tax_receipt is not None,
                "receipt_url": donation.tax_receipt.pdf_url if donation.tax_receipt else None,
                "receipt_number": donation.tax_receipt.receipt_number if donation.tax_receipt else None
            }
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Tracking ID format")

    if pan:
        pan_clean = pan.strip().upper()
        donations = query.join(Donation.donor).filter(Donor.pan_number == pan_clean).order_by(Donation.created_at.desc()).all()
        if not donations:
            raise HTTPException(status_code=404, detail="No donations found for this PAN")
        
        results = []
        for d in donations:
            results.append({
                "donation_id": d.id,
                "donor_name": d.donor.full_name,
                "extracted_utr": d.extracted_utr,
                "amount": float(d.extracted_amount or 0),
                "donation_status": d.status,
                "is_verified": d.is_verified,
                "has_receipt": d.tax_receipt is not None,
                "receipt_url": d.tax_receipt.pdf_url if d.tax_receipt else None,
                "receipt_number": d.tax_receipt.receipt_number if d.tax_receipt else None,
                "date": d.created_at.strftime("%d-%b-%Y")
            })
        return {"status": "found", "records": results}

    raise HTTPException(status_code=400, detail="Please provide either PAN or tracking_id")
