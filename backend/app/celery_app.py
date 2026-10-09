import os
from celery import Celery
from backend.app.config import settings

celery_app = Celery(
    "raise_india_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="tasks.process_screenshot_ocr")
def process_screenshot_ocr_task(donation_id: str, file_path: str, filename_hint: str):
    """
    Celery worker task to process screenshot OCR asynchronously.
    """
    from backend.app.database import SessionLocal
    from backend.app.models import Donation, DonationStatus
    from backend.app.services.ocr_service import OCRService
    from backend.app.services.reconciliation_service import ReconciliationService
    import uuid

    db = SessionLocal()
    try:
        donation = db.query(Donation).filter(Donation.id == uuid.UUID(donation_id)).first()
        if not donation:
            return {"error": "Donation not found"}

        ocr_result = OCRService.process_screenshot(file_path, filename_hint)

        donation.extracted_utr = ocr_result.get("extracted_utr")
        donation.extracted_amount = ocr_result.get("extracted_amount")
        if ocr_result.get("extracted_date"):
            from datetime import datetime
            donation.extracted_date = datetime.fromisoformat(ocr_result["extracted_date"])
        donation.raw_ocr_payload = ocr_result
        donation.ocr_confidence = ocr_result.get("confidence", 0.0)
        donation.status = DonationStatus(ocr_result.get("status", "EXTRACTED"))

        db.commit()

        # Run auto reconciliation
        ReconciliationService.run_reconciliation(db)
        return {"status": "success", "utr": donation.extracted_utr}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
