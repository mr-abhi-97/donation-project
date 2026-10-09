import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Donor
from backend.app.schemas import DonorCreate, DonorResponse
from backend.app.utils.validators import normalize_indian_phone, validate_pan_format

router = APIRouter(prefix="/donors", tags=["Donors"])


@router.post("/", response_model=DonorResponse, status_code=status.HTTP_201_CREATED)
def create_donor(payload: DonorCreate, db: Session = Depends(get_db)):
    """
    Creates or returns existing donor based on PAN number.
    Validates PAN format and normalizes Indian mobile to E.164 (+91XXXXXXXXXX).
    """
    try:
        pan = validate_pan_format(payload.pan_number)
        norm_phone = normalize_indian_phone(payload.phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing = db.query(Donor).filter(Donor.pan_number == pan).first()
    if existing:
        # Update details if provided
        existing.full_name = payload.full_name
        existing.phone = norm_phone
        existing.email = payload.email.strip().lower()
        if payload.address:
            existing.address = payload.address
        db.commit()
        db.refresh(existing)
        return existing

    donor = Donor(
        id=uuid.uuid4(),
        full_name=payload.full_name,
        pan_number=pan,
        phone=norm_phone,
        email=payload.email.strip().lower(),
        address=payload.address
    )
    db.add(donor)
    db.commit()
    db.refresh(donor)
    return donor


@router.get("/", response_model=List[DonorResponse])
def list_donors(
    search: Optional[str] = Query(None, description="Search by Name, PAN, Phone, Email"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Donor)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Donor.full_name.ilike(s)) |
            (Donor.pan_number.ilike(s)) |
            (Donor.phone.ilike(s)) |
            (Donor.email.ilike(s))
        )
    return query.order_by(Donor.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{donor_id}", response_model=DonorResponse)
def get_donor(donor_id: uuid.UUID, db: Session = Depends(get_db)):
    donor = db.query(Donor).filter(Donor.id == donor_id).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    return donor
