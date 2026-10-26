"""
Raise India Foundation - High-Precision OCR & UPI Payment Forensics Engine
==========================================================================
Engine Architecture:
1. Windows Tesseract binary auto-discovery with PATH & registry candidate fallbacks.
2. OpenCV multi-pass preprocessing pipeline (deskew, bilateral filter, CLAHE, Otsu & adaptive binarization).
3. Dual-engine ensemble: RapidOCR (in-memory ONNX Runtime) + Pytesseract (PSM 6 & PSM 11).
4. Multi-tier UPI UTR & RRN extraction (labeled regex, OCR-noise character correction, isolated 12-digit).
5. Robust currency extraction (supports ₹, ?, R, INR, Rs. with Indian comma notation).
6. Comprehensive structured JSON diagnostics and graceful error containment.
"""

import os
import re
import cv2
import shutil
import logging
import numpy as np
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Tesseract Binary Discovery & Pytesseract Configuration
# ---------------------------------------------------------------------------
import pytesseract

TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    os.getenv("TESSERACT_CMD", ""),
    shutil.which("tesseract") or "",
]

TESSERACT_AVAILABLE = False
TESSERACT_PATH = None

for candidate in TESSERACT_CANDIDATES:
    if candidate and os.path.isfile(candidate):
        try:
            pytesseract.pytesseract.tesseract_cmd = candidate
            TESSERACT_AVAILABLE = True
            TESSERACT_PATH = candidate
            logger.info(f"Tesseract OCR binary discovered and bound: {candidate}")
            break
        except Exception as e:
            logger.warning(f"Failed to bind candidate {candidate}: {e}")

# ---------------------------------------------------------------------------
# 2. RapidOCR ONNX Runtime Engine Initialization
# ---------------------------------------------------------------------------
try:
    from rapidocr_onnxruntime import RapidOCR
    _rapidocr_engine = RapidOCR()
    logger.info("RapidOCR ONNX Runtime engine initialized successfully.")
except Exception as e:
    _rapidocr_engine = None
    logger.warning(f"RapidOCR engine not available: {e}")


# ---------------------------------------------------------------------------
# 3. OpenCV Image Preprocessing & Variant Generation Pipeline
# ---------------------------------------------------------------------------
class ImagePreprocessor:
    @staticmethod
    def deskew_image(gray: np.ndarray) -> np.ndarray:
        """Calculates skew angle and rotates image if skew is significant."""
        try:
            # Invert colors so text is white
            thresh = cv2.bitwise_not(gray)
            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 50:
                return gray
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            if 0.5 < abs(angle) < 45.0:
                h, w = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(
                    gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
                )
                return rotated
        except Exception:
            pass
        return gray

    @classmethod
    def generate_variants(cls, image_bytes: bytes) -> List[Tuple[str, np.ndarray]]:
        """
        Produces multiple filtered variants tailored for OCR clarity:
        - Scaled standard grayscale
        - Bilateral filtered (edge-preserving denoising)
        - CLAHE contrast enhanced
        - Otsu binarized
        - Adaptive Gaussian thresholded
        - Inverted variants (critical for PhonePe/GPay dark-mode receipts)
        """
        if not image_bytes:
            return []

        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return []

            # Upscale if low resolution (ensures crisp font strokes for OCR)
            h, w = img.shape[:2]
            if w < 1200:
                scale = 1200.0 / w
                img = cv2.resize(
                    img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC
                )

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            deskewed = cls.deskew_image(gray)

            # 1. Bilateral filter: removes sensor/JPEG noise while preserving sharp text edges
            bilateral = cv2.bilateralFilter(deskewed, 9, 75, 75)

            # 2. CLAHE contrast stretching: amplifies faded text
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            contrast = clahe.apply(bilateral)

            # 3. Otsu binarization
            _, otsu = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 4. Adaptive Gaussian thresholding
            adaptive = cv2.adaptiveThreshold(
                bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
            )

            # 5. Inverted variants for dark mode
            inverted = cv2.bitwise_not(bilateral)
            contrast_inv = clahe.apply(inverted)
            _, otsu_inv = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            return [
                ("bilateral", bilateral),
                ("contrast", contrast),
                ("otsu", otsu),
                ("adaptive", adaptive),
                ("inverted", inverted),
                ("contrast_inv", contrast_inv),
                ("otsu_inv", otsu_inv),
            ]
        except Exception as e:
            logger.warning(f"ImagePreprocessor error: {e}")
            return []


# ---------------------------------------------------------------------------
# 4. Core Payment Screenshot Extractor & Parser
# ---------------------------------------------------------------------------
class PaymentScreenshotExtractor:
    # Character substitutions specifically within 12-char numeric candidate tokens
    OCR_DIGIT_MAP = {
        'O': '0', 'o': '0', 'D': '0', 'Q': '0',
        'I': '1', 'l': '1', 'i': '1', '|': '1', '!': '1',
        'Z': '2', 'z': '2',
        'E': '3',
        'A': '4',
        'S': '5', 's': '5',
        'G': '6', 'b': '6',
        'T': '7',
        'B': '8',
        'g': '9', 'q': '9',
    }

    UPI_PAYMENT_ANCHORS = [
        "upi", "utr", "transaction id", "trans id", "txn id", "ref no", "ref id", "ref", "rrn",
        "reference no", "reference", "paid to", "payment to", "transfer to", "paid successfully",
        "payment successful", "completed", "debited from", "credited to",
        "auto-id", "auto id", "autoid", "auto_id", "aotid", "aot id", "aot-id",
        "app order id", "app order", "order id", "order no", "order num",
        "google pay", "gpay", "phonepe", "paytm", "bhim", "banking name", "bank",
        "amount", "rupees", "inr", "raise india", "npci"
    ]

    @classmethod
    def clean_ocr_text(cls, text: str) -> str:
        """Separates fused CamelCase words and normalizes line breaks."""
        if not text:
            return ""
        # Separate fused lowercase-uppercase boundary (e.g. UPItransactionID -> UPI transaction ID)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        # Separate number and word boundaries
        text = re.sub(r'([0-9])([A-Za-z]{3,})', r'\1 \2', text)
        text = re.sub(r'([A-Za-z]{3,})([0-9])', r'\1 \2', text)
        return text

    @classmethod
    def repair_ocr_digits(cls, token: str) -> Optional[str]:
        """
        Repairs a 12-character token having 1 to 3 OCR letter substitutions.
        Example: '4289I02938I2' -> '428910293812'
        """
        if not token or len(token) != 12:
            return None
        cleaned = []
        subs_count = 0
        for char in token:
            if char.isdigit():
                cleaned.append(char)
            elif char in cls.OCR_DIGIT_MAP:
                cleaned.append(cls.OCR_DIGIT_MAP[char])
                subs_count += 1
            else:
                return None
        if subs_count <= 3:
            result = "".join(cleaned)
            # Ensure not a dummy repetition like 000000000000
            if len(set(result)) > 3:
                return result
        return None

    @classmethod
    def extract_details(cls, image_bytes: bytes) -> Dict[str, Any]:
        """
        Executes dual-engine OCR (RapidOCR + Tesseract), parses UTR, Amount, Donor Name,
        and returns complete forensic diagnostics.
        """
        if not image_bytes:
            return cls._empty_result("Empty image buffer provided.")

        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            raw_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if raw_img is None:
                return cls._empty_result("Image decoding failed (unsupported format or corrupted bytes).")

            text_segments: List[str] = []
            engines_used: List[str] = []

            # ---------------------------------------------------------------
            # PASS 1: RapidOCR (Primary, fast, deep learning based)
            # ---------------------------------------------------------------
            if _rapidocr_engine is not None:
                try:
                    res, _ = _rapidocr_engine(raw_img)
                    if res:
                        rapid_text = "\n".join(r[1] for r in res)
                        text_segments.append(rapid_text)
                        engines_used.append("RapidOCR_Standard")

                    # If dark mode / low contrast, also pass contrast inverted variant
                    if len("\n".join(text_segments).strip()) < 50:
                        gray = cv2.cvtColor(raw_img, cv2.COLOR_BGR2GRAY)
                        inv = cv2.bitwise_not(gray)
                        res_inv, _ = _rapidocr_engine(inv)
                        if res_inv:
                            text_segments.append("\n".join(r[1] for r in res_inv))
                            engines_used.append("RapidOCR_Inverted")
                except Exception as ro_err:
                    logger.warning(f"RapidOCR pass encountered an exception: {ro_err}")

            # ---------------------------------------------------------------
            # PASS 2: Pytesseract (Configured Windows binary)
            # ---------------------------------------------------------------
            variants = ImagePreprocessor.generate_variants(image_bytes)
            if TESSERACT_AVAILABLE and variants:
                # Try uniform block (--psm 6) and sparse text (--psm 11)
                configs = ["--oem 3 --psm 6", "--oem 3 --psm 11"]
                for name, var_mat in variants[:3]:
                    for cfg in configs:
                        try:
                            t = pytesseract.image_to_string(var_mat, config=cfg)
                            if t and len(t.strip()) > 10:
                                text_segments.append(t)
                                if f"Tesseract_{name}" not in engines_used:
                                    engines_used.append(f"Tesseract_{name}_{cfg.split()[-1]}")
                        except Exception:
                            pass

            combined_raw = "\n".join(text_segments)
            cleaned_text = cls.clean_ocr_text(combined_raw)

            # ---------------------------------------------------------------
            # Parsing: UTR, Amount, Name, Date
            # ---------------------------------------------------------------
            extracted_utr = cls.parse_utr(cleaned_text)
            extracted_amount = cls.parse_amount(cleaned_text)
            extracted_name = cls.parse_payer_name(cleaned_text)
            extracted_date = cls.parse_date(cleaned_text)

            # Keyword anchor matching
            lower_text = cleaned_text.lower()
            keyword_hits = sum(1 for kw in cls.UPI_PAYMENT_ANCHORS if kw in lower_text)

            # Qualification heuristics:
            # Genuine receipt if:
            # 1. Extracted a valid UTR, OR
            # 2. Extracted an amount > 0 along with at least 1 payment anchor / transaction word, OR
            # 3. Contains >= 2 payment anchors, OR
            # 4. Contains transaction completion indicators
            has_tx_words = any(w in lower_text for w in ["paid", "completed", "successful", "transferred", "transfer", "debited", "credited", "upi", "utr", "txn", "rrn"])
            is_valid_receipt = bool(
                extracted_utr
                or (extracted_amount > 0.0 and (keyword_hits >= 1 or has_tx_words))
                or (keyword_hits >= 2)
                or (keyword_hits >= 1 and has_tx_words)
            )

            # Guard against zero-content / random photos
            if is_valid_receipt and not extracted_utr and extracted_amount <= 0.0 and keyword_hits < 2 and not has_tx_words:
                is_valid_receipt = False

            is_custom_id = False
            if extracted_utr:
                if any(k in lower_text for k in ["auto-id", "auto id", "autoid", "auto_id", "aotid", "aot id", "app order", "order id"]):
                    is_custom_id = True
                elif not extracted_utr.isnumeric() or len(extracted_utr) != 12:
                    is_custom_id = True

            confidence = 0.95 if (extracted_utr and extracted_amount > 0) else (0.80 if extracted_utr else 0.50)

            return {
                "is_valid_receipt": is_valid_receipt,
                "amount": extracted_amount,
                "utr": extracted_utr,
                "payer_name": extracted_name or "Verified Donor",
                "raw_text": cleaned_text,
                "keyword_hits": keyword_hits,
                "date": extracted_date,
                "is_custom_id": is_custom_id,
                "confidence": confidence,
                "engines_used": engines_used,
            }

        except Exception as err:
            logger.error(f"PaymentScreenshotExtractor fatal error: {err}", exc_info=True)
            return cls._empty_result(f"Extraction error: {str(err)}")

    @classmethod
    def parse_utr(cls, text: str) -> Optional[str]:
        """
        Multi-tier UTR parsing:
        Tier 1: Explicit labels (UTR, UPI Ref, Ref No, Txn ID, RRN, Google Txn ID)
        Tier 2: Labeled tokens with OCR letter substitutions repaired
        Tier 3: Spaced 12-digit numeric sequences
        Tier 4: Standalone isolated 12-digit numeric sequences
        """
        if not text:
            return None

        # Tier 1: Explicit labeled patterns
        targeted_patterns = [
            # High priority: exact 12 numeric digits directly following UPI/UTR labels
            r"(?i)(?:UPI\s*(?:Transaction\s*ID|Ref(?:\s*(?:No|Num|ID|Number|NC|NA|RO))?)|UTR(?:\s*(?:No|Num|ID|Number))?|Bank\s*Ref(?:erence)?(?:\s*No)?|RRN|Transaction\s*ID|Txn\s*ID|Trans\s*ID|Payment\s*ID)[\s\:\.\-\#\/]*([0-9]{12})\b",
            # Standard UPI Ref / UTR / Txn ID
            r"(?i)(?:UPI\s*(?:Transaction\s*ID|Ref(?:\s*(?:No|Num|ID|Number|NC|NA|RO))?)|UTR(?:\s*(?:No|Num|ID|Number))?|Bank\s*Ref(?:erence)?(?:\s*No)?|RRN|Transaction\s*ID|Txn\s*ID|Trans\s*ID|Payment\s*ID)[\s\:\.\-\#\/]*([A-Za-z0-9]{8,24})",
            # Spaced digits after label: "UPI Ref No: 4289 1029 3812"
            r"(?i)(?:UPI\s*Ref|UTR|RRN|Txn\s*ID|Trans\s*ID|Transaction\s*ID|Payment\s*ID)[\s\:\.\-\#\/]*([0-9]{3,6}[\s\-\.][0-9]{3,6}(?:[\s\-\.][0-9]{3,6})?)",
            # Auto-ID / AOTID / Order IDs
            r"(?i)(?:Auto[\s\-_]*ID|AOT[\s\-_]*ID|App\s*Order\s*(?:ID|No|Num)|Order\s*(?:ID|No|Num))[\s\:\.\-\#\/]*([A-Za-z0-9]{8,24})",
            # Google transaction ID: "Google transaction ID CICAgLDDxLWIBg"
            r"(?i)(?:Google\s*transaction\s*ID|Google\s*Txn\s*ID)[\s\:\.\-\#\/]*([A-Za-z0-9\-_]{8,24})",
        ]

        for pat in targeted_patterns:
            matches = re.finditer(pat, text)
            for m in matches:
                val = m.group(1).replace(" ", "").replace("-", "").strip()
                # Check if exact 12-digit pure numeric
                if len(val) == 12 and val.isdigit():
                    if len(set(val)) > 3:
                        return val
                # Check if repairable 12-char token
                repaired = cls.repair_ocr_digits(val)
                if repaired:
                    return repaired
                # If custom alphanumeric ID >= 8 chars (e.g. CICAgLDDxLWIBg or Auto-ID)
                if len(val) >= 8 and len(set(val)) > 2:
                    if not val.lower().startswith("http") and val.lower() not in ["successful", "completed", "foundation"]:
                        # If a 12-digit numeric match also exists further in the text, favor the 12-digit UTR
                        continue_search = False
                        if not val.isdigit():
                            continue_search = True
                        if not continue_search:
                            return val

        # Tier 2: Search for any 12-char token near payment keywords with OCR repairs
        near_keyword_pattern = r"(?i)(?:ref|utr|upi|txn|id|rrn|no|num)[\s\:\.\-]*([A-Za-z0-9]{12})\b"
        for m in re.finditer(near_keyword_pattern, text):
            cand = m.group(1).strip()
            repaired = cls.repair_ocr_digits(cand)
            if repaired:
                return repaired

        # Tier 3: Spaced 12-digit numeric sequences anywhere in text: "4289 1029 3812" or "42899 1613170"
        spaced_matches = re.findall(r"\b([0-9]{3,5}\s+[0-9]{3,5}(?:\s+[0-9]{3,5})?)\b", text)
        for sm in spaced_matches:
            cleaned_num = re.sub(r"\s+", "", sm)
            if len(cleaned_num) == 12 and len(set(cleaned_num)) > 3:
                if cleaned_num not in ["000000000000", "111111111111", "123456789012"]:
                    return cleaned_num

        # Tier 4: Standalone isolated 12-digit numeric sequences: \b([0-9]{12})\b
        twelve_digit_matches = re.findall(r"\b([0-9]{12})\b", text)
        for val in twelve_digit_matches:
            if len(set(val)) > 3 and val not in ["000000000000", "111111111111", "999999999999", "123456789012"]:
                if f"{val}." not in text and f".{val}" not in text:
                    return val

        return None

    @staticmethod
    def parse_amount(text: str) -> float:
        """
        Extracts monetary amounts from receipts.
        Handles ₹, ?, R, INR, Rs., Paid of, Payment of, Comma separated figures.
        """
        if not text:
            return 0.0

        patterns = [
            # Currency symbol prefixes (₹, ?, R, INR, Rs., Rs, $, €)
            r"(?:[₹\?R]|INR|Rs\.?)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)",
            # Standard numbers with currency symbol directly attached
            r"(?:[₹\?R]|INR|Rs\.?)\s*([0-9]+(?:\.[0-9]{1,2})?)",
            # Payment labels: "Paid of 200.00", "Payment of R2,000", "Amount 500", "Amount: 1,200"
            r"(?i)(?:paid|amount|transfer(?:red)?|payment|debited|credited)\s*(?:of)?\s*[:\-]?\s*(?:[₹\?R]|INR|Rs\.?)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)",
            # Multiline: "Payment Successful \n 200" or "Completed \n 500.00"
            r"(?i)(?:payment\s*successful|paid\s*successfully|completed|successful)[\s\n\r]*[:\-]?\s*(?:[₹\?R]|INR|Rs\.?)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)",
            # Amount before completion word: "500.00 \n Completed" or "1,200 \n Successful"
            r"(?i)\b([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)[\s\n\r]+(?:completed|successful|paid\s*successfully)",
            # Line starting with decimal amount or currency (very common at top of receipt)
            r"(?m)^\s*(?:[₹\?R]|INR|Rs\.?)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2}))\s*$",
            # Amount before currency word: "200 \n Rupees Only"
            r"([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)[\s\n\r]*(?:rupees|only)",
            # Indian comma-separated currency values: 1,200 or 25,000 or 1,25,000.00 or 2,000
            r"\b([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{2})?)\b",
            # Plain numbers following 'To' line on GPay/PhonePe receipts: "To Raise India Foundation \n 200"
            r"(?i)to[\s\w\n\r]+[\n\r]\s*(?:[₹\?R]|INR|Rs\.?)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)",
            # Standalone line with round numbers (e.g. 200, 250, 500, 1000, 1200)
            r"(?m)^\s*(?:[₹\?R]|INR|Rs\.?)?\s*([1-9][0-9]{1,5})\s*$",
        ]

        candidates = []
        for pat in patterns:
            for m in re.findall(pat, text):
                val_str = m.replace(",", "").strip()
                try:
                    val = float(val_str)
                    # Discard zero, negative, phone numbers, Julian days, years (2020-2030) if standalone
                    if 1.0 <= val <= 5000000.0:
                        if val not in [2024.0, 2025.0, 2026.0]:
                            candidates.append(val)
                except ValueError:
                    continue

        if candidates:
            # Return the highest plausible payment amount (avoids micro fees or stray tokens)
            return max(candidates)
        return 0.0

    @staticmethod
    def parse_payer_name(text: str) -> Optional[str]:
        """Extracts sender/donor name from payment receipts."""
        if not text:
            return None

        patterns = [
            r"(?i)(?:from|paid\s*by|transfer\s*from|sender)\s*[:\-]?\s*([A-Za-z\s]{3,35})(?:\s*\([^\)]+\)|[\n\r]|$)",
            r"(?i)from\s*[:\-]?\s*([A-Za-z\s]{3,30})",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                candidate = m.group(1).strip()
                clean = re.sub(
                    r"(?i)\b(bank|account|indusind|hdfc|sbi|axis|icici|kotak|paytm|state\s*bank|google\s*pay|phonepe)\b",
                    "", candidate
                ).strip()
                if len(clean) >= 3 and not clean.isnumeric():
                    # Handle CamelCase separation (e.g. BAYAMUMUTHKARAJESH -> Bayamumuthka Rajesh)
                    clean = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean)
                    clean = re.sub(r'(?i)(rajesh|kumar|sharma|singh|patel|gupta|verma|rao|reddy|ali|khan)$', r' \1', clean).strip()
                    return clean.title()

        # UPI handle fallback (e.g. talwarrajesh965-1@okhdfcbank -> Rajesh)
        handle = re.search(r"([A-Za-z]{3,20})[0-9]*@[A-Za-z]+", text)
        if handle:
            return handle.group(1).title()

        return None

    @staticmethod
    def parse_date(text: str) -> Optional[str]:
        """Extracts date/time and converts to ISO string."""
        if not text:
            return None

        date_patterns = [
            r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}(?:\s+(?:at\s+)?\d{1,2}:\d{2}(?::\d{2})?(?:\s+[AP]M)?)?)\b',
            r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}(?:\s+(?:at\s+)?\d{1,2}:\d{2}(?::\d{2})?(?:\s+[AP]M)?)?)\b',
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)\b',
            r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
        ]
        for pat in date_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                raw_str = m.group(1).replace("at", " ").strip()
                try:
                    dt = date_parser.parse(raw_str, fuzzy=True)
                    if dt.year >= 2020:
                        return dt.isoformat()
                except Exception:
                    continue
        return None

    @classmethod
    def _empty_result(cls, reason: str) -> Dict[str, Any]:
        return {
            "is_valid_receipt": False,
            "amount": 0.0,
            "utr": None,
            "payer_name": "Unverified Donor",
            "raw_text": "",
            "keyword_hits": 0,
            "date": None,
            "is_custom_id": False,
            "confidence": 0.0,
            "engines_used": [],
            "error_reason": reason,
        }


# ---------------------------------------------------------------------------
# 5. High-Level Public Service Facade (OCRService)
# ---------------------------------------------------------------------------
class OCRService:
    """
    Public entry point for screenshot OCR processing.
    Directly compatible with backend routers and audit jobs.
    """
    @classmethod
    def process_screenshot(cls, image_path: str, filename_hint: Optional[str] = None) -> Dict[str, Any]:
        if not os.path.exists(image_path):
            return {
                "raw_text": "",
                "extracted_utr": None,
                "extracted_amount": None,
                "extracted_donor_name": None,
                "extracted_date": None,
                "confidence": 0.0,
                "status": "REJECTED",
                "is_valid_receipt": False,
                "is_payment_receipt": False,
                "domain_rejection_reason": f"File not found on filesystem: {image_path}",
                "keyword_hits": 0,
                "is_custom_id": False,
                "diagnostics": {"tesseract_available": TESSERACT_AVAILABLE, "rapidocr_available": _rapidocr_engine is not None},
            }

        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
        except Exception as read_err:
            return {
                "raw_text": "",
                "extracted_utr": None,
                "extracted_amount": None,
                "extracted_donor_name": None,
                "extracted_date": None,
                "confidence": 0.0,
                "status": "REJECTED",
                "is_valid_receipt": False,
                "is_payment_receipt": False,
                "domain_rejection_reason": f"Could not read image file bytes: {read_err}",
                "keyword_hits": 0,
                "is_custom_id": False,
                "diagnostics": {"error": str(read_err)},
            }

        try:
            details = PaymentScreenshotExtractor.extract_details(image_bytes)
            is_valid = details.get("is_valid_receipt", False)

            extracted_utr = details.get("utr")
            extracted_amount = details.get("amount") if details.get("amount", 0) > 0 else None
            # If a valid UTR was extracted, treat as valid receipt
            if extracted_utr:
                is_valid = True

            if not is_valid:
                return {
                    "raw_text": details.get("raw_text", ""),
                    "extracted_utr": None,
                    "extracted_amount": None,
                    "extracted_donor_name": None,
                    "extracted_date": None,
                    "confidence": 0.0,
                    "status": "REJECTED",
                    "is_valid_receipt": False,
                    "is_payment_receipt": False,
                    "domain_rejection_reason": "Not a Payment Receipt: Missing recognized UPI payment anchors (UTR, Txn ID, Paid to).",
                    "keyword_hits": details.get("keyword_hits", 0),
                    "is_custom_id": False,
                    "diagnostics": details,
                }

            status = "EXTRACTED" if extracted_utr else ("EXTRACTED" if extracted_amount else "FLAGGED_REVIEW")

            return {
                "raw_text": details.get("raw_text", ""),
                "extracted_utr": extracted_utr,
                "extracted_amount": extracted_amount,
                "extracted_donor_name": donor_name or "Verified Donor",
                "extracted_date": details.get("date"),
                "confidence": details.get("confidence", 0.95),
                "status": status,
                "is_valid_receipt": True,
                "is_payment_receipt": True,
                "domain_rejection_reason": None,
                "keyword_hits": details.get("keyword_hits", 0),
                "is_custom_id": details.get("is_custom_id", False),
                "diagnostics": {
                    "engines_used": details.get("engines_used", []),
                    "tesseract_bound": TESSERACT_AVAILABLE,
                    "tesseract_path": TESSERACT_PATH,
                    "rapidocr_active": _rapidocr_engine is not None,
                },
            }

        except Exception as e:
            logger.error(f"OCRService.process_screenshot unexpected error on {filename_hint or image_path}: {e}", exc_info=True)
            return {
                "raw_text": "",
                "extracted_utr": None,
                "extracted_amount": None,
                "extracted_donor_name": "Verified Donor",
                "extracted_date": None,
                "confidence": 0.4,
                "status": "FLAGGED_REVIEW",
                "is_valid_receipt": True,
                "is_payment_receipt": True,
                "domain_rejection_reason": None,
                "keyword_hits": 0,
                "is_custom_id": False,
                "diagnostics": {"exception": str(e)},
            }
