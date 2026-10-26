import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Raise India - Donation Reconciliation & OCR Portal"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{BASE_DIR / 'raise_india.db'}"
    )
    
    # Celery & Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    # Upload Directories
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    SCREENSHOTS_DIR: Path = BASE_DIR / "uploads" / "screenshots"
    STATEMENTS_DIR: Path = BASE_DIR / "uploads" / "statements"
    RECEIPTS_DIR: Path = BASE_DIR / "uploads" / "receipts"
    
    # OCR Settings
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "")
    GOOGLE_CLOUD_VISION_KEY_PATH: str = os.getenv("GOOGLE_CLOUD_VISION_KEY_PATH", "")
    
    # NGO 80G Tax Exemption Details
    NGO_NAME: str = "Raise India Foundation"
    NGO_ADDRESS: str = "Plot 42, Sector 18, Institutional Area, New Delhi - 110025, India"
    NGO_PAN: str = "AAATR8291P"
    NGO_80G_REG_NO: str = "AAATR8291PF20214"
    NGO_EMAIL: str = "donations@raiseindia.org"
    NGO_PHONE: str = "+91 11 4567 8900"
    CURRENT_FINANCIAL_YEAR: str = "2024-2025"

    model_config = SettingsConfigDict(case_sensitive=True, extra="allow")

settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
settings.STATEMENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
