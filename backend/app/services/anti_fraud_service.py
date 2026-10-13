import hashlib
import io
import re
import base64
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


class ScreenshotFraudDetector:
    @staticmethod
    def calculate_file_hash(image_bytes: bytes) -> str:
        """
        Calculates SHA-256 hex digest of uploaded file bytes
        to prevent byte-level duplicate screenshot recycling.
        """
        return hashlib.sha256(image_bytes).hexdigest()

    @staticmethod
    def run_error_level_analysis(image_bytes: bytes, quality: int = 90) -> dict:
        """
        Error Level Analysis (ELA) to detect digital photo manipulations,
        cut-and-paste digits, altered amounts, and photoshopped UTR blocks.
        
        1. Decodes image into RGB.
        2. Re-compresses to a temporary JPEG buffer at quality=90.
        3. Computes absolute difference via ImageChops.difference(original, resaved).
        4. Normalizes extrema scale: scale = 255.0 / max_diff.
        5. Computes pixel variance. If variance > 12.5, marks as tampered.
        6. Encodes ELA heatmap as base64 string.
        """
        try:
            original = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            
            # Recompress to temporary in-memory JPEG buffer
            resaved_buffer = io.BytesIO()
            original.save(resaved_buffer, "JPEG", quality=quality)
            resaved_buffer.seek(0)
            resaved = Image.open(resaved_buffer).convert("RGB")

            # Calculate absolute difference
            diff = ImageChops.difference(original, resaved)

            # Extrema scaling
            extrema = diff.getextrema()
            max_diff = max([ex[1] for ex in extrema]) if extrema else 0
            scale = 255.0 / max_diff if max_diff > 0 else 1.0

            # Generate enhanced ELA visualization
            ela_image = ImageEnhance.Brightness(diff).enhance(scale)
            
            # Convert ELA image to base64
            out_buffer = io.BytesIO()
            ela_image.save(out_buffer, format="JPEG", quality=85)
            ela_base64 = base64.b64encode(out_buffer.getvalue()).decode("utf-8")

            # Mathematical analysis of difference
            diff_arr = np.array(diff, dtype=np.float32)
            # Grayscale luminosity of diff
            gray_diff = 0.2989 * diff_arr[:, :, 0] + 0.5870 * diff_arr[:, :, 1] + 0.1140 * diff_arr[:, :, 2]
            
            mean_variance = float(np.var(gray_diff))
            mean_diff = float(np.mean(gray_diff))

            # Tamper evaluation:
            # Recompressed JPEG artifacts in unaltered screenshots are uniformly distributed.
            # Localized splicing / photoshopped text overlays cause high localized error variance.
            is_tampered = bool(mean_variance > 12.5 or mean_diff > 14.0)
            tamper_score = round(min((mean_variance / 25.0) * 100.0, 100.0), 2)

            return {
                "tamper_score": tamper_score,
                "is_tampered": is_tampered,
                "ela_base64": f"data:image/jpeg;base64,{ela_base64}",
                "mean_variance": round(mean_variance, 2),
                "max_difference": int(max_diff)
            }
        except Exception as e:
            # Fallback if image cannot be parsed
            return {
                "tamper_score": 0.0,
                "is_tampered": False,
                "ela_base64": "",
                "mean_variance": 0.0,
                "error": str(e)
            }

    @staticmethod
    def validate_utr_syntax(utr: str, allow_custom_id: bool = False) -> dict:
        r"""
        Validates UPI UTR / Auto-ID / AOTID / App Order ID transaction reference syntax:
        1. Must match 8-24 characters.
        2. Disallows dummy or test sequences (e.g., 000000000000, 111111111111, 123456789012)
        3. Disallows low entropy strings (<= 2 unique characters)
        4. Validates Julian date/year prefix (digits 1-4) for standard 12-digit UPI UTRs.
           Auto-ID, AOTID, and App Order IDs are accepted without Julian constraint when allow_custom_id=True
           or when containing alphanumeric order identifiers.
        """
        if not utr or not isinstance(utr, str):
            return {
                "is_valid": False,
                "rejection_reason": "UTR is missing or null"
            }

        cleaned = utr.strip()

        # 1. Check dummy sequences
        known_dummies = {
            "000000000000",
            "111111111111",
            "999999999999",
            "123456789012",
            "012345678901",
            "987654321098"
        }
        if cleaned in known_dummies:
            return {
                "is_valid": False,
                "rejection_reason": "Dummy or test UTR sequence detected"
            }

        # 2. Check entropy (number of distinct characters)
        if len(set(cleaned)) <= 2:
            return {
                "is_valid": False,
                "rejection_reason": "Insufficient character entropy in transaction reference"
            }

        # 3. Check general format
        if not re.match(r"^[A-Za-z0-9\-_]{8,24}$", cleaned):
            return {
                "is_valid": False,
                "rejection_reason": f"Invalid reference format: '{cleaned}' must be 8-24 alphanumeric characters or 12 numeric digits"
            }

        # 4. Standard 12-digit numeric UPI UTR validation
        if re.match(r"^\d{12}$", cleaned) and not allow_custom_id:
            try:
                julian_day = int(cleaned[1:4])
                if julian_day < 1 or julian_day > 366:
                    return {
                        "is_valid": False,
                        "rejection_reason": f"Invalid Julian day prefix ({cleaned[1:4]}): Days must be between 001 and 366"
                    }
            except ValueError:
                return {
                    "is_valid": False,
                    "rejection_reason": "Invalid Julian day prefix encoding"
                }

        return {
            "is_valid": True,
            "rejection_reason": None
        }

    UPI_PAYMENT_ANCHORS = [
        "upi", "utr", "transaction id", "trans id", "txn id", "ref no", "ref id", "ref", "rrn",
        "reference no", "reference", "paid to", "payment to", "transfer to", "paid successfully",
        "payment successful", "completed", "debited from", "credited to",
        "auto-id", "auto id", "autoid", "auto_id", "aotid", "aot id", "aot-id",
        "app order id", "app order", "order id", "order no", "order num",
        "google pay", "phonepe", "paytm", "bhim", "banking name", "bank", "amount", "rupees", "inr"
    ]

    @classmethod
    def verify_payment_receipt_domain(cls, raw_text: str, filename: str = None) -> dict:
        """
        Strict UPI payment receipt domain verification:
        1. Checks whether extracted OCR text contains genuine UPI payment receipt anchors.
        2. Detects and rejects non-payment random images (fashion, selfies, scenery, general photos).
        3. Returns validation status, matched anchors, and specific rejection reason if invalid.
        """
        text_lower = (raw_text or "").lower()

        # Immediate rejection of non-financial placeholders
        if "[non_financial_media]" in text_lower or "non-financial" in text_lower or "zero transaction" in text_lower:
            return {
                "is_valid": False,
                "rejection_reason": "NON_PAYMENT_IMAGE: Uploaded file does not contain recognized UPI payment receipt anchors (UPI, UTR, Txn ID, Paid to, Google Pay, PhonePe, Paytm, BHIM). Media identified as random non-financial content.",
                "matched_anchors": [],
                "confidence_score": 0.0
            }

        # Check for receipt keywords in filename if provided
        filename_lower = (filename or "").lower()
        known_receipt_filename_tags = [
            "utr", "receipt", "payment", "gpay", "phonepe", "paytm", "bhim",
            "upi", "transaction", "txn", "paid"
        ]
        has_filename_receipt_hint = any(tag in filename_lower for tag in known_receipt_filename_tags)

        # Explicit non-payment markers in filename
        non_payment_tags = [
            "selfie", "fashion", "scenery", "nature", "landscape", "wallpaper",
            "dress", "shirt", "model", "avatar", "profile", "cat", "dog", "car"
        ]
        has_non_payment_tag = any(tag in filename_lower for tag in non_payment_tags)

        # Word boundary search for anchors
        matched_anchors = []
        for anchor in cls.UPI_PAYMENT_ANCHORS:
            if re.search(r'\b' + re.escape(anchor) + r'\b', text_lower):
                matched_anchors.append(anchor)

        if has_non_payment_tag and not matched_anchors:
            return {
                "is_valid": False,
                "rejection_reason": "NON_PAYMENT_IMAGE: Detected non-payment media (selfie/fashion/scenery/photo). Missing all UPI payment anchors.",
                "matched_anchors": [],
                "confidence_score": 0.0
            }

        # Must have at least 1 genuine payment anchor to qualify as a payment receipt
        if len(matched_anchors) >= 2 or (len(matched_anchors) >= 1 and has_filename_receipt_hint):
            return {
                "is_valid": True,
                "rejection_reason": None,
                "matched_anchors": matched_anchors,
                "confidence_score": min(1.0, 0.4 + (len(matched_anchors) * 0.15))
            }
        elif len(matched_anchors) == 1 and not has_non_payment_tag:
            return {
                "is_valid": True,
                "rejection_reason": None,
                "matched_anchors": matched_anchors,
                "confidence_score": 0.65
            }
        else:
            return {
                "is_valid": False,
                "rejection_reason": "NON_PAYMENT_IMAGE: Missing required UPI payment anchors (UPI, UTR, Txn ID, Paid to, Google Pay, PhonePe, Paytm, BHIM). Image identified as non-financial media.",
                "matched_anchors": [],
                "confidence_score": 0.0
            }

    @staticmethod
    def check_duplicate_utr(db, utr: str, current_donation_id=None):
        """
        Queries SQLite database to check if a 12-digit UTR has already been registered.
        Returns the original/earliest Donation record if duplicate exists, else None.
        """
        if not utr or not isinstance(utr, str):
            return None
        clean_utr = utr.strip()
        if not clean_utr:
            return None
        from backend.app.models import Donation
        query = db.query(Donation).filter(Donation.extracted_utr == clean_utr)
        if current_donation_id:
            query = query.filter(Donation.id != current_donation_id)
        return query.order_by(Donation.created_at.asc()).first()

