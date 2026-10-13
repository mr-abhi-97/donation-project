import uuid
import enum
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Numeric,
    DateTime,
    Date,
    Boolean,
    Float,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    TypeDecorator,
    JSON,
    Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB
from backend.app.database import Base

# Universal GUID type decorator for seamless PostgreSQL & SQLite compatibility
class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type if available, otherwise CHAR(36).
    """
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError):
            return value


# Universal JSON type decorator for seamless PostgreSQL JSONB & SQLite JSON compatibility
class UniversalJSON(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_JSONB())
        else:
            return dialect.type_descriptor(JSON())


class DonationStatus(str, enum.Enum):
    PENDING = "PENDING"
    PENDING_OCR = "PENDING_OCR"
    EXTRACTED = "EXTRACTED"
    MATCHED = "MATCHED"
    SUCCESS = "SUCCESS"
    FLAGGED_REVIEW = "FLAGGED_REVIEW"
    DUPLICATE_FLAGGED = "DUPLICATE_FLAGGED"
    REJECTED = "REJECTED"


class Donor(Base):
    __tablename__ = "donors"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    pan_number = Column(String(10), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    donations = relationship("Donation", back_populates="donor", cascade="all, delete-orphan")


class Donation(Base):
    __tablename__ = "donations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    donor_id = Column(GUID(), ForeignKey("donors.id", ondelete="SET NULL"), nullable=True)
    screenshot_url = Column(Text, nullable=False)
    extracted_utr = Column(String(20), index=True, nullable=True)
    extracted_amount = Column(Numeric(10, 2), nullable=True)
    extracted_date = Column(DateTime, nullable=True)
    raw_ocr_payload = Column(UniversalJSON(), nullable=True)
    ocr_confidence = Column(Float, default=0.0)
    status = Column(
        SQLEnum(DonationStatus, name="donation_status_enum", native_enum=False),
        default=DonationStatus.PENDING_OCR,
        nullable=False,
        index=True
    )
    matched_statement_id = Column(
        GUID(), 
        ForeignKey("bank_statement_entries.id", ondelete="SET NULL"), 
        nullable=True
    )
    is_verified = Column(Boolean, default=False, nullable=False, index=True)
    flagged_reason = Column(Text, nullable=True)

    # 1. Anti-Fraud & Duplicate Prevention
    image_sha256 = Column(String(64), index=True, nullable=True)
    tamper_score = Column(Float, default=0.0)
    ela_heatmap_url = Column(Text, nullable=True)
    is_flagged_fraud = Column(Boolean, default=False, index=True)
    fraud_reasons = Column(UniversalJSON(), default=list)

    # Duplicate UTR Tracking & Reference Metadata
    original_transaction_id = Column(GUID(), nullable=True, index=True)
    original_transaction_hash = Column(String(64), nullable=True)
    duplicate_metadata = Column(UniversalJSON(), nullable=True)

    # 2. CA Audit Trail (Mandatory for Form 10BD & 80G Inspection)
    verified_by_user = Column(String(100), nullable=True)  # Admin username or email
    verified_at = Column(DateTime, nullable=True)
    bank_matched_mode = Column(String(50), nullable=True)  # AUTO_EXACT, AUTO_FUZZY, MANUAL_OVERRIDE
    admin_audit_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Index: Disallow double 80G certificates against verified UTRs & optimize queries
    __table_args__ = (
        Index('idx_verified_utr_status', 'extracted_utr', 'is_verified'),
    )

    @property
    def is_duplicate_utr(self) -> bool:
        return self.status == DonationStatus.DUPLICATE_FLAGGED or bool(self.original_transaction_id)

    @property
    def donor_name(self) -> Optional[str]:
        return self.donor.full_name if self.donor else "Verified Donor"

    # Relationships
    donor = relationship("Donor", back_populates="donations")
    matched_statement = relationship("BankStatementEntry", back_populates="donations")
    tax_receipt = relationship("TaxReceipt80G", back_populates="donation", uselist=False, cascade="all, delete-orphan")


class BankStatementEntry(Base):
    __tablename__ = "bank_statement_entries"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    transaction_date = Column(Date, nullable=False, index=True)
    narration = Column(Text, nullable=False)
    extracted_utr = Column(String(20), index=True, nullable=True)
    credit_amount = Column(Numeric(10, 2), nullable=False)
    balance = Column(Numeric(12, 2), nullable=True)
    is_reconciled = Column(Boolean, default=False, nullable=False, index=True)
    statement_batch_id = Column(String(100), nullable=True)

    # Mathematical & Source Integrity Audit
    is_balance_continuous = Column(Boolean, default=True)
    is_suspicious_pdf_source = Column(Boolean, default=False)
    math_discrepancy_details = Column(UniversalJSON(), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    donations = relationship("Donation", back_populates="matched_statement")


class TaxReceipt80G(Base):
    __tablename__ = "tax_receipts_80g"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    donation_id = Column(GUID(), ForeignKey("donations.id", ondelete="CASCADE"), unique=True, nullable=False)
    receipt_number = Column(String(50), unique=True, nullable=False, index=True)
    financial_year = Column(String(20), nullable=False)
    eligible_amount = Column(Numeric(10, 2), nullable=False)
    pdf_path = Column(Text, nullable=False)
    pdf_url = Column(Text, nullable=False)
    issued_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    donation = relationship("Donation", back_populates="tax_receipt")


# Alias for backward compatibility & standard references
TaxReceipt = TaxReceipt80G
