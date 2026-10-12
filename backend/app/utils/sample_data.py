import os
import io
import uuid
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from PIL import Image, ImageDraw, ImageFont

from backend.app.config import settings
from backend.app.database import SessionLocal, Base, engine
from backend.app.models import Donor, Donation, BankStatementEntry, DonationStatus, TaxReceipt80G
from backend.app.services.ocr_service import OCRService
from backend.app.services.reconciliation_service import ReconciliationService
from backend.app.services.receipt_service import ReceiptService
from backend.app.services.anti_fraud_service import ScreenshotFraudDetector
from backend.app.utils.validators import normalize_indian_phone


def create_mock_upi_screenshot(filename: str, app_name: str, amount: float, utr: str, txn_date_str: str) -> str:
    """
    Creates a realistic UPI payment screenshot image using PIL.
    """
    width, height = 480, 840
    bg_color = (248, 250, 252)
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Top App Bar
    app_header_color = (30, 64, 175) if app_name == "GPay" else ((107, 33, 168) if app_name == "PhonePe" else (15, 118, 110))
    draw.rectangle([(0, 0), (width, 80)], fill=app_header_color)
    draw.text((20, 28), f"{app_name} UPI Transfer", fill=(255, 255, 255))

    # Center card
    card_margin = 25
    draw.rounded_rectangle([(card_margin, 100), (width - card_margin, 780)], radius=16, fill=(255, 255, 255), outline=(226, 232, 240), width=2)

    # Success Green Circle
    circle_center = (width // 2, 170)
    circle_radius = 35
    draw.ellipse([
        (circle_center[0] - circle_radius, circle_center[1] - circle_radius),
        (circle_center[0] + circle_radius, circle_center[1] + circle_radius)
    ], fill=(16, 185, 129))
    # Checkmark
    draw.line([(circle_center[0] - 15, circle_center[1]), (circle_center[0] - 5, circle_center[1] + 12)], fill=(255, 255, 255), width=4)
    draw.line([(circle_center[0] - 5, circle_center[1] + 12), (circle_center[0] + 18, circle_center[1] - 12)], fill=(255, 255, 255), width=4)

    draw.text((width // 2 - 80, 220), "Payment Successful", fill=(16, 185, 129))
    draw.text((width // 2 - 70, 260), f"₹{amount:,.2f}", fill=(17, 24, 39))

    draw.text((card_margin + 20, 340), "Paid to", fill=(107, 114, 128))
    draw.text((card_margin + 20, 365), "Raise India Foundation", fill=(17, 24, 39))
    draw.text((card_margin + 20, 390), "UPI ID: raiseindia@sbi", fill=(107, 114, 128))

    draw.line([(card_margin + 20, 425), (width - card_margin - 20, 425)], fill=(229, 231, 235), width=1)
    draw.text((card_margin + 20, 450), "Transaction Details", fill=(31, 41, 55))

    details = [
        ("UPI Ref No / UTR", utr),
        ("Date & Time", txn_date_str),
        ("Debited From", "HDFC Bank •••• 4128"),
        ("Google / Txn ID", f"CICAgID{utr[:6]}"),
    ]

    y_pos = 485
    for label, val in details:
        draw.text((card_margin + 20, y_pos), label, fill=(107, 114, 128))
        draw.text((card_margin + 20, y_pos + 20), val, fill=(17, 24, 39))
        y_pos += 55

    draw.text((width // 2 - 100, 740), "POWERED BY UPI • NPCI", fill=(156, 163, 175))

    file_path = settings.SCREENSHOTS_DIR / filename
    img.save(file_path, "PNG")
    return f"/uploads/screenshots/{filename}"


def seed_sample_data():
    """
    Seeds initial realistic donors, donation screenshots with anti-fraud analysis,
    and continuous bank statements.
    """
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Donation).count() > 0:
            print("Database already contains donation records. Skipping seed.")
            return

        print("Seeding demo data for Raise India...")

        # 1. Create sample donors with normalized E.164 phone numbers
        donor1 = Donor(
            id=uuid.uuid4(),
            full_name="Rajesh Kumar Verma",
            pan_number="ABCDE1234F",
            phone=normalize_indian_phone("9876543210"),
            email="rajesh.verma@example.com",
            address="Flat 402, Sunshine Apts, Indiranagar, Bengaluru - 560038"
        )
        donor2 = Donor(
            id=uuid.uuid4(),
            full_name="Dr. Arjun Sharma",
            pan_number="BKAPS8192K",
            phone=normalize_indian_phone("9811234567"),
            email="arjun.sharma@example.com",
            address="14/B, Civil Lines, Jaipur - 302006"
        )
        donor3 = Donor(
            id=uuid.uuid4(),
            full_name="Neha Gupta",
            pan_number="GHJKL5678M",
            phone=normalize_indian_phone("9712345678"),
            email="neha.gupta@example.com",
            address="703, Tower C, Godrej Woods, Noida - 201301"
        )
        donor4 = Donor(
            id=uuid.uuid4(),
            full_name="Vikram Mehta",
            pan_number="MNOPQ9012R",
            phone=normalize_indian_phone("9988776655"),
            email="vikram.mehta@example.com",
            address="Plot 55, Marine Drive, Mumbai - 400020"
        )
        donor5 = Donor(
            id=uuid.uuid4(),
            full_name="Ananya Iyer",
            pan_number="STUVW3456T",
            phone=normalize_indian_phone("9845012345"),
            email="ananya.iyer@example.com",
            address="88, Anna Nagar West, Chennai - 600040"
        )

        db.add_all([donor1, donor2, donor3, donor4, donor5])
        db.flush()

        # 2. Generate sample payment screenshots
        url1 = create_mock_upi_screenshot("gpay_receipt_428910293812.png", "GPay", 5000.0, "428910293812", "09 Oct 2024, 10:15 AM")
        url2 = create_mock_upi_screenshot("phonepe_receipt_392019482019.png", "PhonePe", 11000.0, "392019482019", "09 Oct 2024, 11:30 AM")
        url3 = create_mock_upi_screenshot("paytm_receipt_410293847561.png", "Paytm", 2500.0, "410293847561", "08 Oct 2024, 04:45 PM")
        url4 = create_mock_upi_screenshot("bhim_receipt_fuzzy_482910482910.png", "BHIM", 21000.0, "482910482910", "07 Oct 2024, 02:10 PM")
        url5 = create_mock_upi_screenshot("unmatched_receipt_998877665544.png", "GPay", 7500.0, "998877665544", "06 Oct 2024, 09:00 AM")
        url6 = create_mock_upi_screenshot("tampered_receipt_000000000000.png", "PhonePe", 50000.0, "000000000000", "05 Oct 2024, 12:00 PM")

        # 2b. Non-payment image
        img7 = Image.new("RGB", (480, 840), color=(135, 206, 235))
        d7 = ImageDraw.Draw(img7)
        d7.text((50, 400), "Scenic Mountain Landscape Nature Wallpaper", fill=(255, 255, 255))
        p7 = settings.SCREENSHOTS_DIR / "wallpaper_scenery.png"
        img7.save(p7, "PNG")
        url7 = "/uploads/screenshots/wallpaper_scenery.png"

        # 3. Create bank statement entries with continuous running balances
        batch_id = "INIT_DEMO"
        stmt1 = BankStatementEntry(
            id=uuid.uuid4(),
            transaction_date=date(2024, 10, 9),
            narration="UPI/428910293812/CR/PAYTM/RAJESH VERMA/DONATION",
            extracted_utr="428910293812",
            credit_amount=Decimal("5000.00"),
            balance=Decimal("1250000.00"),
            is_reconciled=False,
            statement_batch_id=batch_id,
            is_balance_continuous=True,
            is_suspicious_pdf_source=False
        )
        stmt2 = BankStatementEntry(
            id=uuid.uuid4(),
            transaction_date=date(2024, 10, 9),
            narration="UPI/392019482019/CR/GPAY/DR ARJUN SHARMA/DONATION 80G",
            extracted_utr="392019482019",
            credit_amount=Decimal("11000.00"),
            balance=Decimal("1261000.00"),
            is_reconciled=False,
            statement_batch_id=batch_id,
            is_balance_continuous=True,
            is_suspicious_pdf_source=False
        )
        stmt3 = BankStatementEntry(
            id=uuid.uuid4(),
            transaction_date=date(2024, 10, 8),
            narration="CMS/410293847561/NEHA GUPTA/CHILD WELFARE CONTRIBUTION",
            extracted_utr="410293847561",
            credit_amount=Decimal("2500.00"),
            balance=Decimal("1263500.00"),
            is_reconciled=False,
            statement_batch_id=batch_id,
            is_balance_continuous=True,
            is_suspicious_pdf_source=False
        )
        # Statement with slight typo in bank narration (Fuzzy candidate demo: 482910482911 vs 482910482910)
        stmt4 = BankStatementEntry(
            id=uuid.uuid4(),
            transaction_date=date(2024, 10, 7),
            narration="UPI/482910482911/CR/BHIM/VIKRAM MEHTA/FOOD RELIEF",
            extracted_utr="482910482911",
            credit_amount=Decimal("21000.00"),
            balance=Decimal("1284500.00"),
            is_reconciled=False,
            statement_batch_id=batch_id,
            is_balance_continuous=True,
            is_suspicious_pdf_source=False
        )
        stmt5 = BankStatementEntry(
            id=uuid.uuid4(),
            transaction_date=date(2024, 10, 9),
            narration="UPI/771122334455/CR/PHONEPE/DIRECT QR DONATION/ANON",
            extracted_utr="771122334455",
            credit_amount=Decimal("10000.00"),
            balance=Decimal("1294500.00"),
            is_reconciled=False,
            statement_batch_id=batch_id,
            is_balance_continuous=True,
            is_suspicious_pdf_source=False
        )

        db.add_all([stmt1, stmt2, stmt3, stmt4, stmt5])
        db.flush()

        # Helper to compute SHA-256 and ELA for a screenshot file
        def inspect_img(fname):
            p = settings.SCREENSHOTS_DIR / fname
            if p.exists():
                with open(p, "rb") as f:
                    b = f.read()
                h = ScreenshotFraudDetector.calculate_file_hash(b)
                ela = ScreenshotFraudDetector.run_error_level_analysis(b)
                return h, ela.get("tamper_score", 0.0), ela.get("ela_base64", "")
            return None, 0.0, ""

        h1, t1, e1 = inspect_img("gpay_receipt_428910293812.png")
        h2, t2, e2 = inspect_img("phonepe_receipt_392019482019.png")
        h3, t3, e3 = inspect_img("paytm_receipt_410293847561.png")
        h4, t4, e4 = inspect_img("bhim_receipt_fuzzy_482910482910.png")
        h5, t5, e5 = inspect_img("unmatched_receipt_998877665544.png")
        h6, t6, e6 = inspect_img("tampered_receipt_000000000000.png")

        # 4. Create donations with anti-fraud metadata
        don1 = Donation(
            id=uuid.uuid4(),
            donor_id=donor1.id,
            screenshot_url=url1,
            extracted_utr="428910293812",
            extracted_amount=Decimal("5000.00"),
            extracted_date=datetime(2024, 10, 9, 10, 15, tzinfo=timezone.utc),
            ocr_confidence=0.96,
            status=DonationStatus.EXTRACTED,
            is_verified=False,
            image_sha256=h1,
            tamper_score=t1,
            ela_heatmap_url=e1,
            is_flagged_fraud=False
        )
        don2 = Donation(
            id=uuid.uuid4(),
            donor_id=donor2.id,
            screenshot_url=url2,
            extracted_utr="392019482019",
            extracted_amount=Decimal("11000.00"),
            extracted_date=datetime(2024, 10, 9, 11, 30, tzinfo=timezone.utc),
            ocr_confidence=0.94,
            status=DonationStatus.EXTRACTED,
            is_verified=False,
            image_sha256=h2,
            tamper_score=t2,
            ela_heatmap_url=e2,
            is_flagged_fraud=False
        )
        don3 = Donation(
            id=uuid.uuid4(),
            donor_id=donor3.id,
            screenshot_url=url3,
            extracted_utr="410293847561",
            extracted_amount=Decimal("2500.00"),
            extracted_date=datetime(2024, 10, 8, 16, 45, tzinfo=timezone.utc),
            ocr_confidence=0.92,
            status=DonationStatus.EXTRACTED,
            is_verified=False,
            image_sha256=h3,
            tamper_score=t3,
            ela_heatmap_url=e3,
            is_flagged_fraud=False
        )
        don4 = Donation(
            id=uuid.uuid4(),
            donor_id=donor4.id,
            screenshot_url=url4,
            extracted_utr="482910482910",
            extracted_amount=Decimal("21000.00"),
            extracted_date=datetime(2024, 10, 7, 14, 10, tzinfo=timezone.utc),
            ocr_confidence=0.88,
            status=DonationStatus.FLAGGED_REVIEW,
            flagged_reason="Fuzzy UTR match (distance 1): Extracted 482910482910 vs Bank 482910482911. Amount ₹21,000 matches exactly.",
            matched_statement_id=None,
            is_verified=False,
            image_sha256=h4,
            tamper_score=t4,
            ela_heatmap_url=e4,
            is_flagged_fraud=False
        )
        don5 = Donation(
            id=uuid.uuid4(),
            donor_id=donor5.id,
            screenshot_url=url5,
            extracted_utr="998877665544",
            extracted_amount=Decimal("7500.00"),
            extracted_date=datetime(2024, 10, 6, 9, 0, tzinfo=timezone.utc),
            ocr_confidence=0.91,
            status=DonationStatus.EXTRACTED,
            is_verified=False,
            image_sha256=h5,
            tamper_score=t5,
            ela_heatmap_url=e5,
            is_flagged_fraud=False
        )
        # 6. Flagged Fraud demo donation (Dummy UTR sequence & high tamper demo)
        don6 = Donation(
            id=uuid.uuid4(),
            donor_id=donor5.id,
            screenshot_url=url6,
            extracted_utr="000000000000",
            extracted_amount=Decimal("50000.00"),
            extracted_date=datetime(2024, 10, 5, 12, 0, tzinfo=timezone.utc),
            ocr_confidence=0.85,
            status=DonationStatus.FLAGGED_REVIEW,
            flagged_reason="FLAGGED FOR FRAUD: Dummy/Test UTR sequence (000000000000) | Suspected digital tampering",
            is_verified=False,
            image_sha256=h6,
            tamper_score=85.4,
            ela_heatmap_url=e6,
            is_flagged_fraud=True,
            fraud_reasons=[
                "INVALID_UTR_SYNTAX: Dummy or test UTR sequence detected",
                "HIGH_ELA_SCORE: Error Level Analysis detected non-uniform JPEG recompression (85.4%)"
            ]
        # 7. Non-Payment Image Demo (Rejected as non-financial media)
        with open(p7, "rb") as f7:
            b7 = f7.read()
        h7 = ScreenshotFraudDetector.calculate_file_hash(b7)
        don7 = Donation(
            id=uuid.uuid4(),
            donor_id=donor5.id,
            screenshot_url=url7,
            extracted_utr=None,
            extracted_amount=None,
            extracted_date=datetime(2024, 10, 4, 15, 30, tzinfo=timezone.utc),
            ocr_confidence=0.0,
            status=DonationStatus.REJECTED,
            flagged_reason="NON_PAYMENT_IMAGE: Missing required UPI/Bank payment anchors.",
            is_verified=False,
            image_sha256=h7,
            tamper_score=0.0,
            ela_heatmap_url="",
            is_flagged_fraud=True,
            fraud_reasons=[
                "NON_PAYMENT_IMAGE: Missing required UPI/Bank payment anchors."
            ]
        )

        db.add_all([don1, don2, don3, don4, don5, don6, don7])
        db.commit()

        # Run auto-reconciliation to match don1, don2, don3
        ReconciliationService.run_reconciliation(db)

        # Generate sample 80G tax receipts for verified donations
        verified_donations = db.query(Donation).filter(Donation.is_verified == True).all()
        for idx, vd in enumerate(verified_donations, 1):
            receipt_no = ReceiptService.generate_receipt_number(idx)
            pdf_path = ReceiptService.generate_80g_pdf(vd, vd.donor, receipt_no)
            pdf_url = f"/api/receipts/download/{receipt_no.replace('/', '_')}.pdf"
            tax_rec = TaxReceipt80G(
                id=uuid.uuid4(),
                donation_id=vd.id,
                receipt_number=receipt_no,
                financial_year=settings.CURRENT_FINANCIAL_YEAR,
                eligible_amount=vd.extracted_amount or Decimal("0.0"),
                pdf_path=str(pdf_path),
                pdf_url=pdf_url
            )
            db.add(tax_rec)
        db.commit()

        print("Demo data seeded, anti-fraud reconciliation complete, and 80G receipts issued!")
    finally:
        db.close()
