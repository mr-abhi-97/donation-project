from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import re

from backend.app.models import DonationStatus
from backend.app.utils.validators import normalize_indian_phone, validate_pan_format

try:
    from pydantic import validator
    HAS_V1_VALIDATOR = True
except ImportError:
    from pydantic import field_validator
    HAS_V1_VALIDATOR = False


def to_pydantic(model_cls, obj):
    if hasattr(model_cls, 'model_validate'):
        return model_cls.model_validate(obj)
    return model_cls.from_orm(obj)


class DonorBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name as per PAN")
    pan_number: str = Field(..., min_length=10, max_length=10, description="10-digit PAN number")
    phone: str = Field(..., min_length=10, max_length=20, description="Contact phone number")
    email: str = Field(..., description="Valid email address")
    address: Optional[str] = Field(None, description="Donor address for Form 10BD")

    if HAS_V1_VALIDATOR:
        @validator("pan_number")
        def validate_pan(cls, v):
            return validate_pan_format(v)

        @validator("phone")
        def validate_phone(cls, v):
            return normalize_indian_phone(v)


class DonorCreate(DonorBase):
    pass


class DonorResponse(DonorBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class BankStatementEntryBase(BaseModel):
    transaction_date: date
    narration: str
    credit_amount: Decimal
    balance: Optional[Decimal] = None
    extracted_utr: Optional[str] = None


class BankStatementEntryCreate(BankStatementEntryBase):
    statement_batch_id: Optional[str] = None


class BankStatementEntryResponse(BankStatementEntryBase):
    id: UUID
    is_reconciled: bool
    statement_batch_id: Optional[str] = None
    is_balance_continuous: bool = True
    is_suspicious_pdf_source: bool = False
    math_discrepancy_details: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class TaxReceiptResponse(BaseModel):
    id: UUID
    donation_id: UUID
    receipt_number: str
    financial_year: str
    eligible_amount: Decimal
    pdf_path: str
    pdf_url: str
    issued_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class DonationUpdate(BaseModel):
    extracted_utr: Optional[str] = None
    extracted_amount: Optional[Decimal] = None
    extracted_date: Optional[datetime] = None
    status: Optional[DonationStatus] = None
    is_verified: Optional[bool] = None
    flagged_reason: Optional[str] = None
    matched_statement_id: Optional[UUID] = None
    admin_audit_notes: Optional[str] = None
    original_transaction_id: Optional[UUID] = None
    original_transaction_hash: Optional[str] = None
    duplicate_metadata: Optional[Dict[str, Any]] = None


class VerifyDonationRequest(BaseModel):
    verified_by_user: Optional[str] = "Admin / CA Auditor"
    admin_audit_notes: Optional[str] = None
    bank_matched_mode: Optional[str] = "MANUAL_OVERRIDE"


class DonationResponse(BaseModel):
    id: UUID
    donor_id: Optional[UUID] = None
    donor: Optional[DonorResponse] = None
    donor_name: Optional[str] = None
    screenshot_url: str
    extracted_utr: Optional[str] = None
    extracted_amount: Optional[Decimal] = None
    extracted_date: Optional[datetime] = None
    raw_ocr_payload: Optional[Dict[str, Any]] = None
    ocr_confidence: float = 0.0
    status: DonationStatus
    matched_statement_id: Optional[UUID] = None
    matched_statement: Optional[BankStatementEntryResponse] = None
    is_verified: bool
    flagged_reason: Optional[str] = None
    
    # Anti-Fraud & Media Inspection
    image_sha256: Optional[str] = None
    tamper_score: float = 0.0
    ela_heatmap_url: Optional[str] = None
    is_flagged_fraud: bool = False
    fraud_reasons: Optional[List[str]] = None

    # Duplicate UTR Tracking & Metadata
    original_transaction_id: Optional[UUID] = None
    original_transaction_hash: Optional[str] = None
    duplicate_metadata: Optional[Dict[str, Any]] = None
    is_duplicate_utr: bool = False

    # CA Audit Trail
    verified_by_user: Optional[str] = None
    verified_at: Optional[datetime] = None
    bank_matched_mode: Optional[str] = None
    admin_audit_notes: Optional[str] = None

    tax_receipt: Optional[TaxReceiptResponse] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True


class PublicDonationSubmissionResponse(BaseModel):
    tracking_id: UUID
    donor: DonorResponse
    donation_id: UUID
    extracted_utr: Optional[str] = None
    extracted_amount: Optional[Decimal] = None
    status: DonationStatus
    is_flagged_fraud: bool = False
    tamper_score: float = 0.0
    fraud_reasons: Optional[List[str]] = None
    original_transaction_id: Optional[UUID] = None
    original_transaction_hash: Optional[str] = None
    duplicate_metadata: Optional[Dict[str, Any]] = None
    is_duplicate_utr: bool = False
    message: str

    class Config:
        orm_mode = True
        from_attributes = True


class ReconciliationStatsResponse(BaseModel):
    total_donations: int
    matched_count: int
    pending_count: int
    flagged_count: int
    rejected_count: int
    total_amount_collected: Decimal
    reconciled_amount: Decimal
    match_rate_percentage: float
    total_statement_entries: int
    unreconciled_statement_count: int
    fraud_flagged_count: int = 0
    duplicate_flagged_count: int = 0


class FuzzyCandidateResponse(BaseModel):
    statement_entry: BankStatementEntryResponse
    utr_distance: int
    amount_diff: Decimal
    days_diff: int
    confidence_score: float
    match_type: str


class Form10BDItem(BaseModel):
    serial_number: int
    pre_ack_number: str
    id_type: str = "Permanent Account Number (PAN)"
    id_number: str
    donor_name: str
    address: str
    donation_type: str = "Corpus / Specific Purpose"
    mode_of_receipt: str = "Electronic modes including UPI"
    amount: Decimal
    section: str = "Section 80G(5)(vi)"
