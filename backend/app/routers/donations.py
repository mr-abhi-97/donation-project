import os
from pathlib import Path
import uuid
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import Donation, Donor, BankStatementEntry, TaxReceipt80G, DonationStatus
from backend.app.schemas import (
    DonationResponse, DonationUpdate, PublicDonationSubmissionResponse, DonorResponse, 
    VerifyDonationRequest, BatchDeleteRequest, to_pydantic
)
from backend.app.services.storage_service import StorageService
from backend.app.services.ocr_service import OCRService
from backend.app.services.reconciliation_service import ReconciliationService
from backend.app.services.receipt_service import ReceiptService
from backend.app.services.anti_fraud_service import ScreenshotFraudDetector
import logging
from backend.app.services.notification_service import NotificationService
from backend.app.utils.validators import normalize_indian_phone, validate_pan_format

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/donations", tags=["Donations"])


@router.post("/public-submit", response_model=PublicDonationSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def public_submit_donation(
    background_tasks: BackgroundTasks,
    full_name: str = Form(...),
    pan_number: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    address: Optional[str] = Form(None),
    amount_paid: Optional[float] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Public Donor Portal endpoint with Anti-Fraud Inspection:
    1. Validates PAN & normalizes phone to E.164 (+91XXXXXXXXXX).
    2. Computes SHA-256 file hash to block recycled/duplicate screenshots.
    3. Runs Error Level Analysis (ELA) to detect photoshopped amounts/UTRs.
    4. Executes OCR to extract 12-digit UTR and verifies Julian date / syntax.
    5. Flags fraud or saves donation and enqueues bank reconciliation.
    """
    # 1. Validate PAN & normalize phone
    try:
        pan_cleaned = validate_pan_format(pan_number)
        norm_phone = normalize_indian_phone(phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Read file bytes for hash and fraud inspection
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 3. Compute SHA-256 file hash
    file_sha256 = ScreenshotFraudDetector.calculate_file_hash(image_bytes)

    fraud_reasons = []
    is_flagged_fraud = False

    # Check byte-level duplicate recycling
    duplicate_hash_entry = db.query(Donation).filter(Donation.image_sha256 == file_sha256).first()
    if duplicate_hash_entry:
        is_flagged_fraud = True
        fraud_reasons.append("DUPLICATE_FILE_HASH: Identical screenshot bytes already submitted in system.")

    # 4. Error Level Analysis (ELA)
    ela_res = ScreenshotFraudDetector.run_error_level_analysis(image_bytes)
    tamper_score = ela_res.get("tamper_score", 0.0)
    ela_base64 = ela_res.get("ela_base64", "")
    if ela_res.get("is_tampered"):
        is_flagged_fraud = True
        fraud_reasons.append(f"HIGH_ELA_SCORE: Error Level Analysis detected localized image tampering (Score: {tamper_score}%).")

    # 5. Get or create Donor
    donor = db.query(Donor).filter(Donor.pan_number == pan_cleaned).first()
    if not donor:
        donor = Donor(
            id=uuid.uuid4(),
            full_name=full_name.strip(),
            pan_number=pan_cleaned,
            phone=norm_phone,
            email=email.strip().lower(),
            address=address.strip() if address else None
        )
        db.add(donor)
        db.flush()
    else:
        donor.full_name = full_name.strip()
        donor.phone = norm_phone
        donor.email = email.strip().lower()
        if address:
            donor.address = address.strip()

    # 6. Save Screenshot to disk
    rel_url, saved_path = StorageService.save_bytes(image_bytes, file.filename, settings.SCREENSHOTS_DIR)

    # 7. OCR Extraction
    ocr_result = OCRService.process_screenshot(str(saved_path), file.filename)
    raw_ocr_text = ocr_result.get("raw_text", "")

    # Domain & Receipt Verification (Reject non-payment media like selfies/fashion/scenery)
    domain_check = ScreenshotFraudDetector.verify_payment_receipt_domain(raw_ocr_text, file.filename)
    is_valid_receipt = domain_check["is_valid"] and ocr_result.get("is_valid_receipt", False)
    if not is_valid_receipt:
        is_flagged_fraud = True
        rejection_msg = domain_check.get("rejection_reason") or "NON_PAYMENT_IMAGE: Not a payment receipt (missing UPI payment anchors)."
        if rejection_msg not in fraud_reasons:
            fraud_reasons.append(rejection_msg)

    extracted_utr = ocr_result.get("extracted_utr") if is_valid_receipt else None
    extracted_amt = ocr_result.get("extracted_amount") if is_valid_receipt else None
    if amount_paid and not extracted_amt and is_valid_receipt:
        extracted_amt = amount_paid

    extracted_date = None
    if ocr_result.get("extracted_date"):
        try:
            extracted_date = datetime.fromisoformat(ocr_result["extracted_date"])
        except Exception:
            extracted_date = datetime.now(timezone.utc)

    # 8. UTR Syntax Validation & Duplicate Detection
    original_donation = None
    original_tx_id = None
    original_tx_hash = None
    duplicate_meta = None

    if extracted_utr:
        is_custom = ocr_result.get("is_custom_id", False)
        utr_check = ScreenshotFraudDetector.validate_utr_syntax(extracted_utr, allow_custom_id=is_custom)
        if not utr_check["is_valid"]:
            is_flagged_fraud = True
            fraud_reasons.append(f"INVALID_UTR_SYNTAX: {utr_check['rejection_reason']}")

        # Query SQLite database to verify if extracted UTR already exists
        if is_valid_receipt:
            clean_utr = extracted_utr.strip()
            original_donation = ScreenshotFraudDetector.check_duplicate_utr(db, clean_utr)
            if original_donation:
                is_flagged_fraud = True
                original_tx_id = original_donation.id
                original_tx_hash = original_donation.image_sha256
                duplicate_meta = {
                    "original_transaction_id": str(original_tx_id),
                    "original_transaction_hash": original_tx_hash,
                    "original_created_at": original_donation.created_at.isoformat() if original_donation.created_at else None,
                    "original_donor_name": original_donation.donor_name,
                    "original_amount": float(original_donation.extracted_amount) if original_donation.extracted_amount else None,
                    "duplicate_utr": clean_utr,
                    "flagged_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "DUPLICATE_UTR_DETECTED"
                }
                fraud_reasons.append(
                    f"DUPLICATE_UTR: 12-digit UTR '{clean_utr}' already exists in transaction {original_tx_id} (Hash: {original_tx_hash or 'N/A'}). Potential recycling fraud / duplicate submission."
                )

    # Determine status
    if not is_valid_receipt:
        status_val = DonationStatus.REJECTED
        flagged_reason = " | ".join(fraud_reasons)
    elif original_donation:
        status_val = DonationStatus.DUPLICATE_FLAGGED
        flagged_reason = f"Duplicate UTR detected: '{extracted_utr}' already registered in transaction {original_donation.id}."
    elif is_flagged_fraud:
        status_val = DonationStatus.FLAGGED_REVIEW
        flagged_reason = " | ".join(fraud_reasons)
    else:
        status_val = DonationStatus.EXTRACTED
        flagged_reason = None

    # 9. Create Donation record
    donation = Donation(
        id=uuid.uuid4(),
        donor_id=donor.id,
        screenshot_url=rel_url,
        extracted_utr=extracted_utr,
        extracted_amount=Decimal(str(extracted_amt)) if extracted_amt else None,
        extracted_date=extracted_date,
        raw_ocr_payload=ocr_result,
        ocr_confidence=ocr_result.get("confidence", 0.85),
        status=status_val,
        is_verified=False,
        flagged_reason=flagged_reason,
        # Anti-fraud fields
        image_sha256=file_sha256,
        tamper_score=tamper_score,
        ela_heatmap_url=ela_base64,
        is_flagged_fraud=is_flagged_fraud,
        fraud_reasons=list(fraud_reasons or []),
        # Duplicate UTR reference metadata
        original_transaction_id=original_tx_id,
        original_transaction_hash=original_tx_hash,
        duplicate_metadata=duplicate_meta
    )
    db.add(donation)
    try:
        db.commit()
        db.refresh(donation)
    except Exception as db_err:
        db.rollback()
        logger.error(f"Database error during public donation submit: {db_err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operational error saving donation: {str(db_err)}"
        )

    # 10. Run auto reconciliation in background ONLY if not fraudulent and not duplicate
    if not is_flagged_fraud and status_val != DonationStatus.DUPLICATE_FLAGGED:
        background_tasks.add_task(ReconciliationService.run_reconciliation)

    return PublicDonationSubmissionResponse(
        tracking_id=donation.id,
        donor=to_pydantic(DonorResponse, donor),
        donation_id=donation.id,
        extracted_utr=donation.extracted_utr,
        extracted_amount=donation.extracted_amount,
        status=donation.status,
        is_flagged_fraud=donation.is_flagged_fraud,
        tamper_score=donation.tamper_score,
        fraud_reasons=donation.fraud_reasons,
        message="Thank you! Your donation proof has been received. Your 80G tax certificate will be sent to your WhatsApp and email upon bank clearance."
    )


def _process_single_image(img_data: bytes, filename: str, fixed_donor: Optional[Donor], db: Session) -> Optional[Donation]:
    if not img_data or len(img_data) == 0:
        logger.warning(f"Skipping empty image file: {filename}")
        return None

    safe_filename = os.path.basename(filename or "screenshot.png")

    try:
        sha256_hash = ScreenshotFraudDetector.calculate_file_hash(img_data)
        ela_res = ScreenshotFraudDetector.run_error_level_analysis(img_data)

        fraud_reasons = []
        is_fraud = False

        # Duplicate hash check
        if db.query(Donation).filter(Donation.image_sha256 == sha256_hash).first():
            is_fraud = True
            fraud_reasons.append("DUPLICATE_FILE_HASH: Identical screenshot bytes already submitted in system.")

        if ela_res.get("is_tampered"):
            is_fraud = True
            fraud_reasons.append(f"HIGH_ELA_SCORE: Tampering detected (Score: {ela_res.get('tamper_score')}%)")

        rel_url, img_path = StorageService.save_bytes(img_data, safe_filename, settings.SCREENSHOTS_DIR)
        ocr_res = OCRService.process_screenshot(str(img_path), safe_filename)

        # Strict Payment Receipt Domain Verification
        domain_check = ScreenshotFraudDetector.verify_payment_receipt_domain(ocr_res.get("raw_text", ""), safe_filename)
        is_valid_receipt = domain_check.get("is_valid", False) and ocr_res.get("is_valid_receipt", False) and ocr_res.get("status") != "REJECTED"
        if not is_valid_receipt:
            is_fraud = True
            rejection_msg = domain_check.get("rejection_reason") or "NON_PAYMENT_IMAGE: Missing UPI payment anchors (Not a payment receipt)."
            if rejection_msg not in fraud_reasons:
                fraud_reasons.append(rejection_msg)

        # Determine donor attribution
        if fixed_donor:
            assigned_donor = fixed_donor
        else:
            extracted_name = ocr_res.get("extracted_donor_name") if is_valid_receipt else "Unverified Donor"
            if not extracted_name:
                extracted_name = "Verified Donor" if is_valid_receipt else "Unverified Donor"
            assigned_donor = Donor(
                id=uuid.uuid4(),
                full_name=extracted_name,
                pan_number="AAAAA0000A",
                phone="+919876543210",
                email=f"donor_{uuid.uuid4().hex[:6]}@raiseindia.org"
            )
            db.add(assigned_donor)
            db.flush()

        extracted_utr = ocr_res.get("extracted_utr")
        if extracted_utr:
            is_valid_receipt = True
            extracted_utr = str(extracted_utr).strip()[:20]
            is_custom = ocr_res.get("is_custom_id", False)
            utr_syntax = ScreenshotFraudDetector.validate_utr_syntax(extracted_utr, allow_custom_id=is_custom)
            if not utr_syntax.get("is_valid", False):
                is_fraud = True
                fraud_reasons.append(f"INVALID_UTR_SYNTAX: {utr_syntax.get('rejection_reason', 'Invalid UTR format')}")

        # Check if extracted UTR already exists in database (Duplicate UTR Anti-Fraud Guard)
        existing_dup_entry = None
        original_tx_id = None
        original_tx_hash = None
        dup_meta = None
        if extracted_utr and is_valid_receipt:
            existing_dup_entry = ScreenshotFraudDetector.check_duplicate_utr(db, extracted_utr)
            if existing_dup_entry:
                is_fraud = True
                original_tx_id = existing_dup_entry.id
                original_tx_hash = existing_dup_entry.image_sha256
                dup_meta = {
                    "original_transaction_id": str(original_tx_id),
                    "original_transaction_hash": original_tx_hash,
                    "original_created_at": existing_dup_entry.created_at.isoformat() if existing_dup_entry.created_at else None,
                    "original_donor_name": existing_dup_entry.donor_name,
                    "original_amount": float(existing_dup_entry.extracted_amount) if existing_dup_entry.extracted_amount else None,
                    "duplicate_utr": extracted_utr,
                    "flagged_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "DUPLICATE_UTR_DETECTED"
                }
                fraud_reasons.append(
                    f"DUPLICATE_UTR: 12-digit UTR '{extracted_utr}' already exists in transaction {original_tx_id} (Hash: {original_tx_hash or 'N/A'}). Potential recycling fraud / duplicate submission."
                )

        has_utr = bool(extracted_utr)
        has_amount = bool(ocr_res.get("extracted_amount"))
        has_anchors = domain_check.get("is_valid", False) or ocr_res.get("is_valid_receipt", False)
        is_genuine = has_utr or (has_amount and has_anchors) or has_anchors

        extracted_amount_val = None
        if not is_genuine and ocr_res.get("status") == "REJECTED":
            status_val = DonationStatus.REJECTED
            is_verified_val = False
            matched_stmt_id = None
            extracted_utr = None
        elif existing_dup_entry:
            # Block bank reconciliation for duplicate record to avoid double crediting
            status_val = DonationStatus.DUPLICATE_FLAGGED
            is_verified_val = False
            matched_stmt_id = None
        elif is_fraud:
            status_val = DonationStatus.FLAGGED_REVIEW
            is_verified_val = False
            matched_stmt_id = None
        else:
            # Invariant: Payment screenshots remain strictly at status = 'EXTRACTED' (Awaiting bank credit)
            status_val = DonationStatus.EXTRACTED
            is_verified_val = False
            matched_stmt_id = None

        if ocr_res.get("extracted_amount") and status_val != DonationStatus.REJECTED:
            try:
                extracted_amount_val = Decimal(str(ocr_res["extracted_amount"]))
            except Exception:
                extracted_amount_val = None

        extracted_date_val = None
        if ocr_res.get("extracted_date"):
            try:
                extracted_date_val = datetime.fromisoformat(str(ocr_res["extracted_date"]))
            except Exception:
                extracted_date_val = datetime.now(timezone.utc)

        donation = Donation(
            id=uuid.uuid4(),
            donor_id=assigned_donor.id if assigned_donor else None,
            screenshot_url=rel_url,
            extracted_utr=extracted_utr,
            extracted_amount=extracted_amount_val,
            extracted_date=extracted_date_val,
            raw_ocr_payload=ocr_res if isinstance(ocr_res, dict) else {},
            ocr_confidence=float(ocr_res.get("confidence", 0.85)) if domain_check.get("is_valid", False) else 0.0,
            status=status_val,
            matched_statement_id=matched_stmt_id,
            is_verified=is_verified_val,
            image_sha256=sha256_hash,
            tamper_score=float(ela_res.get("tamper_score", 0.0)),
            ela_heatmap_url=ela_res.get("ela_base64", ""),
            is_flagged_fraud=bool(is_fraud),
            fraud_reasons=list(fraud_reasons or []),
            flagged_reason=" | ".join(fraud_reasons) if fraud_reasons else None,
            # Duplicate UTR reference metadata
            original_transaction_id=original_tx_id,
            original_transaction_hash=original_tx_hash,
            duplicate_metadata=dup_meta
        )
        db.add(donation)
        db.flush()
        return donation
    except Exception as img_err:
        logger.error(f"Error processing image '{safe_filename}': {img_err}", exc_info=True)
        return None


@router.post("/bulk-upload", status_code=status.HTTP_200_OK)
async def bulk_upload_screenshots(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    donor_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Admin Bulk Screenshot Upload endpoint with Anti-Fraud Inspection and automated Donor attribution.
    - Accepts multi-file uploads or ZIP archives containing receipt screenshots.
    - Wraps file processing in strict try-except blocks to prevent unhandled exceptions and socket drops.
    - Extracts ZIP archives securely to backend/uploads/screenshots/ and runs OCR forensics.
    - Returns clean JSON with success status, processed count, and extracted donations list.
    """
    try:
        # Ensure screenshots upload directory exists and is writable
        os.makedirs("backend/uploads/screenshots", exist_ok=True)
        settings.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

        created_donations = []
        has_fixed_donor = bool(donor_name and donor_name.strip())
        fixed_donor = None
        if has_fixed_donor:
            clean_donor_name = donor_name.strip()
            fixed_donor = Donor(
                id=uuid.uuid4(),
                full_name=clean_donor_name,
                pan_number="AAAAA0000A",
                phone="+919876543210",
                email=f"donor_{uuid.uuid4().hex[:6]}@raiseindia.org"
            )
            db.add(fixed_donor)
            try:
                db.flush()
            except Exception as d_err:
                db.rollback()
                logger.error(f"Error creating fixed donor: {d_err}")
                fixed_donor = None

        for f in files:
            try:
                filename = f.filename or "screenshot.png"
                filename_lower = filename.lower()

                # Check if zip archive
                if filename_lower.endswith(".zip"):
                    file_bytes = await f.read()
                    import io
                    try:
                        with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as zip_ref:
                            for member in zip_ref.namelist():
                                try:
                                    if member.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.jfif', '.bmp')) and not member.startswith(('__MACOSX', '.')):
                                        img_data = zip_ref.read(member)
                                        member_name = os.path.basename(member)
                                        if img_data and len(img_data) > 0:
                                            don = _process_single_image(img_data, member_name, fixed_donor, db)
                                            if don:
                                                created_donations.append(don)
                                except Exception as member_err:
                                    logger.error(f"Error processing zip member '{member}': {member_err}", exc_info=True)
                                    continue
                    except Exception as zip_err:
                        logger.error(f"Error reading zip archive '{filename}': {zip_err}", exc_info=True)
                        continue
                else:
                    img_data = await f.read()
                    if img_data and len(img_data) > 0:
                        don = _process_single_image(img_data, filename, fixed_donor, db)
                        if don:
                            created_donations.append(don)
            except Exception as file_err:
                logger.error(f"Failed processing file '{getattr(f, 'filename', 'unknown')}': {file_err}", exc_info=True)
                continue

        try:
            db.commit()
        except Exception as db_err:
            db.rollback()
            logger.error(f"Database error during bulk upload commit: {db_err}", exc_info=True)
            return {
                "success": False,
                "message": f"Database error during bulk upload: {str(db_err)}",
                "processed_count": 0,
                "donations": []
            }

        ids = [d.id for d in created_donations]
        result_donations = []
        if ids:
            result_donations = db.query(Donation).options(
                joinedload(Donation.donor),
                joinedload(Donation.matched_statement),
                joinedload(Donation.tax_receipt)
            ).filter(Donation.id.in_(ids)).order_by(Donation.created_at.desc()).all()

        # Enqueue background reconciliation safely
        try:
            background_tasks.add_task(ReconciliationService.run_reconciliation)
        except Exception as bg_err:
            logger.warning(f"Failed to enqueue reconciliation background task: {bg_err}")

        serialized_donations = []
        for d in result_donations:
            try:
                serialized_donations.append(to_pydantic(d, DonationResponse).model_dump(mode="json"))
            except Exception as ser_err:
                logger.warning(f"Error serializing donation {d.id}: {ser_err}")
                serialized_donations.append({"id": str(d.id), "status": str(d.status.value if hasattr(d.status, 'value') else d.status)})

        count = len(result_donations)
        return {
            "success": True,
            "message": f"Successfully processed {count} receipt(s).",
            "processed_count": count,
            "donations": serialized_donations
        }
    except Exception as fatal_err:
        logger.error(f"Fatal error in bulk_upload_screenshots: {fatal_err}", exc_info=True)
        return {
            "success": False,
            "message": f"Bulk upload failed: {str(fatal_err)}",
            "processed_count": 0,
            "donations": []
        }


@router.get("", response_model=List[DonationResponse])
@router.get("/", response_model=List[DonationResponse])
def list_donations(
    skip: int = 0,
    limit: int = 200,
    status: Optional[str] = None,
    search: Optional[str] = None,
    is_verified: Optional[bool] = None,
    is_flagged_fraud: Optional[bool] = None,
    offset: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Donation).options(
        joinedload(Donation.donor),
        joinedload(Donation.matched_statement),
        joinedload(Donation.tax_receipt)
    )

    status_val = status if isinstance(status, str) else None
    if status_val and status_val.upper() != "ALL":
        query = query.filter(Donation.status == status_val.upper())

    search_val = search if isinstance(search, str) else None
    if search_val and search_val.strip():
        s = f"%{search_val.strip()}%"
        query = query.filter(
            or_(
                Donation.extracted_utr.ilike(s),
                Donation.flagged_reason.ilike(s)
            )
        )

    if isinstance(is_verified, bool):
        query = query.filter(Donation.is_verified == is_verified)

    if isinstance(is_flagged_fraud, bool):
        query = query.filter(Donation.is_flagged_fraud == is_flagged_fraud)

    effective_skip = offset if isinstance(offset, int) and offset >= 0 else skip
    offset_val = effective_skip if isinstance(effective_skip, int) and effective_skip >= 0 else 0
    limit_val = limit if isinstance(limit, int) and limit > 0 else 200

    return query.order_by(Donation.created_at.desc()).offset(offset_val).limit(limit_val).all()


@router.post("/batch-delete", status_code=status.HTTP_200_OK)
@router.delete("/batch-delete", status_code=status.HTTP_200_OK)
def batch_delete_donations(
    payload: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    Batch-delete multiple donation records by ID list.
    For each donation:
      1. Unlinks any matched bank statement entry (sets is_reconciled=False).
      2. Deletes associated TaxReceipt80G record.
      3. Removes the screenshot file from disk if it exists.
      4. Deletes the Donation row itself.
    Returns counts of deleted vs not-found IDs.
    """

    if not payload.ids or len(payload.ids) == 0:
        raise HTTPException(status_code=400, detail="ids list cannot be empty")

    deleted_count = 0
    not_found_count = 0

    for raw_id in payload.ids:
        try:
            parsed_id = uuid.UUID(str(raw_id))
        except (ValueError, TypeError):
            parsed_id = raw_id

        donation = db.query(Donation).filter(
            (Donation.id == raw_id) | (Donation.id == parsed_id)
        ).first()

        if not donation:
            not_found_count += 1
            continue

        # 1. Unlink matched bank statement
        if donation.matched_statement_id:
            stmt = db.query(BankStatementEntry).filter(
                BankStatementEntry.id == donation.matched_statement_id
            ).first()
            if stmt:
                stmt.is_reconciled = False

        # 2. Delete associated tax receipt
        db.query(TaxReceipt80G).filter(
            (TaxReceipt80G.donation_id == donation.id) | (TaxReceipt80G.donation_id == str(donation.id))
        ).delete(synchronize_session=False)

        # 3. Remove screenshot file from disk
        if donation.screenshot_url:
            try:
                raw_path = Path(donation.screenshot_url)
                if raw_path.is_absolute() and raw_path.exists():
                    raw_path.unlink()
                    logger.info(f"Deleted screenshot file (abs): {raw_path}")
                else:
                    rel_path = donation.screenshot_url.lstrip("/").replace("\\", "/")
                    if rel_path.startswith("uploads/"):
                        abs_path = settings.UPLOAD_DIR.parent / rel_path
                    else:
                        abs_path = settings.UPLOAD_DIR / rel_path
                    if abs_path.exists():
                        abs_path.unlink()
                        logger.info(f"Deleted screenshot file: {abs_path}")
            except Exception as file_err:
                logger.warning(f"Could not delete screenshot file for donation {donation.id}: {file_err}")

        # 4. Delete the donation record
        db.delete(donation)
        deleted_count += 1

    try:
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.error(f"Database error during batch delete commit: {db_err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during batch delete: {str(db_err)}"
        )

    return {
        "status": "success",
        "success": True,
        "deleted_count": deleted_count,
        "not_found_count": not_found_count,
        "message": f"Batch delete complete: {deleted_count} deleted, {not_found_count} not found."
    }


@router.post("/reset-ledger", status_code=status.HTTP_200_OK)
@router.delete("/reset-ledger", status_code=status.HTTP_200_OK)
def reset_ledger(db: Session = Depends(get_db)):
    """
    Nuclear reset: Wipes ALL donation records, tax receipts, bank statement entries,
    orphaned donors, and removes all uploaded files (screenshots, receipts, statements).
    Returns summary counts of rows and files purged.
    """
    try:
        # Count rows before deletion for audit summary
        donation_count = db.query(Donation).count()
        receipt_count = db.query(TaxReceipt80G).count()
        statement_count = db.query(BankStatementEntry).count()
        donor_count = db.query(Donor).count()

        # Delete in foreign-key safe order
        db.query(TaxReceipt80G).delete(synchronize_session=False)
        db.query(Donation).delete(synchronize_session=False)
        db.query(BankStatementEntry).delete(synchronize_session=False)
        db.query(Donor).delete(synchronize_session=False)
        db.commit()

        # Purge all uploaded files from disk
        files_purged = 0
        for subdir_name in ["screenshots", "receipts", "statements"]:
            subdir = settings.UPLOAD_DIR / subdir_name
            if subdir.exists():
                for fpath in subdir.iterdir():
                    if fpath.is_file() and fpath.name != ".gitkeep":
                        try:
                            fpath.unlink()
                            files_purged += 1
                        except Exception as f_err:
                            logger.warning(f"Could not delete file {fpath}: {f_err}")

        logger.info(
            f"LEDGER RESET: Purged {donation_count} donations, {receipt_count} receipts, "
            f"{statement_count} statements, {donor_count} donors, {files_purged} files."
        )

        return {
            "status": "success",
            "success": True,
            "deleted_count": donation_count,
            "donations_deleted": donation_count,
            "receipts_deleted": receipt_count,
            "statements_deleted": statement_count,
            "donors_deleted": donor_count,
            "files_purged": files_purged,
            "message": f"Ledger reset complete. Purged {donation_count} donations, {receipt_count} receipts, {statement_count} statements, {donor_count} donors, {files_purged} files."
        }
    except Exception as err:
        db.rollback()
        logger.error(f"Ledger reset failed: {err}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ledger reset failed: {str(err)}"
        )


@router.get("/{donation_id}", response_model=DonationResponse)
def get_donation(donation_id: uuid.UUID, db: Session = Depends(get_db)):
    donation = db.query(Donation).options(
        joinedload(Donation.donor),
        joinedload(Donation.matched_statement),
        joinedload(Donation.tax_receipt)
    ).filter(Donation.id == donation_id).first()

    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found")
    return donation


@router.patch("/{donation_id}", response_model=DonationResponse)
def update_donation(
    donation_id: uuid.UUID,
    payload: DonationUpdate,
    db: Session = Depends(get_db)
):
    """
    Inline edit & save endpoint for admin to correct misread OCR digits and record audit notes.
    Re-validates UTR syntax and triggers reconciliation.
    """
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found")

    if payload.extracted_utr is not None:
        clean_utr = payload.extracted_utr.strip()
        donation.extracted_utr = clean_utr

        # Check duplicate UTR against database
        dup_entry = ScreenshotFraudDetector.check_duplicate_utr(db, clean_utr, current_donation_id=donation.id)
        if dup_entry:
            donation.is_flagged_fraud = True
            donation.status = DonationStatus.DUPLICATE_FLAGGED
            donation.is_verified = False
            # Unlink any existing matched statement to prevent double crediting
            if donation.matched_statement_id:
                old_stmt = db.query(BankStatementEntry).filter(BankStatementEntry.id == donation.matched_statement_id).first()
                if old_stmt:
                    old_stmt.is_reconciled = False
                donation.matched_statement_id = None
            donation.original_transaction_id = dup_entry.id
            donation.original_transaction_hash = dup_entry.image_sha256
            donation.duplicate_metadata = {
                "original_transaction_id": str(dup_entry.id),
                "original_transaction_hash": dup_entry.image_sha256,
                "original_created_at": dup_entry.created_at.isoformat() if dup_entry.created_at else None,
                "original_donor_name": dup_entry.donor_name,
                "original_amount": float(dup_entry.extracted_amount) if dup_entry.extracted_amount else None,
                "duplicate_utr": clean_utr,
                "flagged_at": datetime.now(timezone.utc).isoformat(),
                "reason": "DUPLICATE_UTR_DETECTED"
            }
            reasons = list(donation.fraud_reasons or [])
            reasons = [r for r in reasons if not r.startswith("DUPLICATE_UTR")]
            reasons.append(f"DUPLICATE_UTR: 12-digit UTR '{clean_utr}' already exists in transaction {dup_entry.id}.")
            donation.fraud_reasons = reasons
            donation.flagged_reason = f"Duplicate UTR detected: '{clean_utr}' already registered in transaction {dup_entry.id}."
        else:
            # Clear previous duplicate flags if fixed
            donation.original_transaction_id = None
            donation.original_transaction_hash = None
            donation.duplicate_metadata = None
            reasons = [r for r in (donation.fraud_reasons or []) if not r.startswith("DUPLICATE_UTR")]
            donation.fraud_reasons = reasons

            # Validate syntax
            is_custom = not clean_utr.isnumeric() or len(clean_utr) != 12
            utr_check = ScreenshotFraudDetector.validate_utr_syntax(clean_utr, allow_custom_id=is_custom)
            if not utr_check["is_valid"]:
                donation.is_flagged_fraud = True
                reasons = list(donation.fraud_reasons or [])
                reasons.append(f"INVALID_UTR_SYNTAX: {utr_check['rejection_reason']}")
                donation.fraud_reasons = reasons
                donation.flagged_reason = utr_check["rejection_reason"]
            else:
                # If previously flagged only for UTR, clear
                reasons = [r for r in (donation.fraud_reasons or []) if not r.startswith("INVALID_UTR_SYNTAX")]
                donation.fraud_reasons = reasons
                if not reasons:
                    donation.is_flagged_fraud = False
                    donation.flagged_reason = None

            # Check if matching bank statement exists for this newly updated UTR
            matching_stmt = db.query(BankStatementEntry).filter(
                BankStatementEntry.extracted_utr == clean_utr
            ).first()
            if matching_stmt:
                donation.status = DonationStatus.MATCHED
                donation.is_verified = True
                donation.matched_statement_id = matching_stmt.id
                donation.bank_matched_mode = "MANUAL_EDIT_MATCH"
                donation.verified_at = datetime.now(timezone.utc)
                donation.verified_by_user = "INLINE_EDIT"
                matching_stmt.is_reconciled = True

    if payload.extracted_amount is not None:
        donation.extracted_amount = payload.extracted_amount
    if payload.extracted_date is not None:
        donation.extracted_date = payload.extracted_date
    if payload.status is not None:
        donation.status = payload.status
    if payload.is_verified is not None:
        donation.is_verified = payload.is_verified
    if payload.flagged_reason is not None:
        donation.flagged_reason = payload.flagged_reason
    if payload.matched_statement_id is not None:
        donation.matched_statement_id = payload.matched_statement_id
    if payload.admin_audit_notes is not None:
        donation.admin_audit_notes = payload.admin_audit_notes

    donation.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Re-evaluate reconciliation live
    ReconciliationService.run_reconciliation(db)

    db.refresh(donation)
    return donation


@router.patch("/{donation_id}/edit", response_model=DonationResponse)
def update_donation_edit(
    donation_id: uuid.UUID,
    payload: DonationUpdate,
    db: Session = Depends(get_db)
):
    """Alias route for inline UTR edit from frontend cockpit."""
    return update_donation(donation_id=donation_id, payload=payload, db=db)


@router.post("/{donation_id}/verify", response_model=DonationResponse)
def verify_donation(
    donation_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    payload: Optional[VerifyDonationRequest] = None,
    verified_by_user: Optional[str] = Query(None),
    admin_audit_notes: Optional[str] = Query(None),
    bank_matched_mode: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Mark as Verified (with CA Audit Trail, Double-Issuance Block, & WhatsApp Dispatch):
    1. Enforces uniqueness: Blocks double 80G issuance against the same verified UTR.
    2. Logs CA Auditor identity, audit notes, verification timestamp, and match mode.
    3. Issues Section 80G Tax Exemption Certificate PDF.
    4. Dispatches receipt via WhatsApp to donor's mobile number in background.
    """
    donation = db.query(Donation).options(
        joinedload(Donation.donor),
        joinedload(Donation.matched_statement),
        joinedload(Donation.tax_receipt)
    ).filter(Donation.id == donation_id).first()

    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    # 1. Double Issuance Guard
    if donation.extracted_utr:
        duplicate_verified = db.query(Donation).filter(
            Donation.extracted_utr == donation.extracted_utr,
            Donation.is_verified == True,
            Donation.id != donation.id
        ).first()
        if duplicate_verified:
            raise HTTPException(
                status_code=400,
                detail=f"Double issuance blocked! Section 80G certificate has already been issued for UTR '{donation.extracted_utr}' on donation record {duplicate_verified.id}."
            )

    # 2. Update status and audit trail
    donation.is_verified = True
    donation.status = DonationStatus.MATCHED
    donation.flagged_reason = None
    donation.is_flagged_fraud = False

    # CA Audit Trail
    verifier = (payload and payload.verified_by_user) or verified_by_user or "CA Auditor / Admin"
    notes = (payload and payload.admin_audit_notes) or admin_audit_notes or "Verified against official bank credit"
    mode = (payload and payload.bank_matched_mode) or bank_matched_mode or "MANUAL_OVERRIDE"

    donation.verified_by_user = verifier
    donation.verified_at = datetime.now(timezone.utc)
    donation.bank_matched_mode = mode
    donation.admin_audit_notes = notes

    if donation.matched_statement:
        donation.matched_statement.is_reconciled = True

    # 3. Generate 80G Tax Receipt
    if not donation.tax_receipt:
        if not donation.donor:
            donor_name = "UPI Donor"
            if donation.matched_statement and donation.matched_statement.narration:
                parts = donation.matched_statement.narration.split('/')
                if len(parts) >= 5 and parts[4].strip():
                    donor_name = parts[4].strip()
            fallback_donor = Donor(
                id=uuid.uuid4(),
                full_name=donor_name,
                pan_number="AAAAA0000A",
                phone="+919876543210",
                email="donor@raiseindia.org"
            )
            db.add(fallback_donor)
            db.flush()
            donation.donor_id = fallback_donor.id
            donation.donor = fallback_donor

        receipt_count = db.query(TaxReceipt80G).count() + 1
        receipt_no = ReceiptService.generate_receipt_number(receipt_count)
        
        pdf_path = ReceiptService.generate_80g_pdf(donation, donation.donor, receipt_no)
        pdf_url = f"/api/receipts/download/{receipt_no.replace('/', '_')}.pdf"

        tax_rec = TaxReceipt80G(
            id=uuid.uuid4(),
            donation_id=donation.id,
            receipt_number=receipt_no,
            financial_year=settings.CURRENT_FINANCIAL_YEAR,
            eligible_amount=donation.extracted_amount or Decimal("0.0"),
            pdf_path=str(pdf_path),
            pdf_url=pdf_url
        )
        db.add(tax_rec)
        db.flush()

        # 4. Enqueue WhatsApp Notification to Donor
        if donation.donor.phone:
            background_tasks.add_task(
                NotificationService.send_whatsapp_80g_receipt,
                phone=donation.donor.phone,
                donor_name=donation.donor.full_name,
                receipt_url=pdf_url,
                amount=float(donation.extracted_amount or 0.0),
                receipt_number=receipt_no
            )

    db.commit()
    db.refresh(donation)
    return donation


@router.post("/{donation_id}/reject", response_model=DonationResponse)
def reject_donation(
    donation_id: uuid.UUID,
    reason: Optional[str] = Query("Marked as invalid / duplicate by admin"),
    db: Session = Depends(get_db)
):
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")

    donation.status = DonationStatus.REJECTED
    donation.is_verified = False
    donation.flagged_reason = reason
    
    if donation.matched_statement_id:
        st = db.query(BankStatementEntry).filter(BankStatementEntry.id == donation.matched_statement_id).first()
        if st:
            st.is_reconciled = False
        donation.matched_statement_id = None

    db.commit()
    db.refresh(donation)
    return donation


@router.delete("/{donation_id}", status_code=status.HTTP_200_OK)
def delete_donation(donation_id: str, db: Session = Depends(get_db)):
    try:
        parsed_id = uuid.UUID(donation_id)
    except ValueError:
        parsed_id = donation_id

    donation = db.query(Donation).filter((Donation.id == donation_id) | (Donation.id == parsed_id)).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation record not found")

    # Unlink matched bank statement if any
    if donation.matched_statement_id:
        stmt = db.query(BankStatementEntry).filter(BankStatementEntry.id == donation.matched_statement_id).first()
        if stmt:
            stmt.is_reconciled = False

    # Remove receipt records if any
    db.query(TaxReceipt80G).filter(
        (TaxReceipt80G.donation_id == donation.id) | (TaxReceipt80G.donation_id == donation_id)
    ).delete(synchronize_session=False)

    db.delete(donation)
    db.commit()
    return {"status": "success", "message": f"Donation {donation_id} deleted successfully"}


