"""
Raise India Foundation - OCR Service Facade
===========================================
Re-exports the high-precision OCR engine from `backend.app.services.ocr` for
100% backward and forward compatibility across existing routers and services.
"""

from backend.app.services.ocr import (
    OCRService,
    PaymentScreenshotExtractor,
    ImagePreprocessor,
    TESSERACT_AVAILABLE,
    TESSERACT_PATH,
)

__all__ = [
    "OCRService",
    "PaymentScreenshotExtractor",
    "ImagePreprocessor",
    "TESSERACT_AVAILABLE",
    "TESSERACT_PATH",
]
