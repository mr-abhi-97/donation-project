from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.routers import donors, donations, bank_statement, reconciliation, receipts
from backend.app.utils.sample_data import seed_sample_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    # Seed initial test data
    try:
        seed_sample_data()
    except Exception as e:
        print(f"Warning: sample data seed failed or already present: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Automated UPI donation reconciliation, OCR verification, and 80G tax receipt issuance system for Raise India Foundation.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploaded screenshots and generated receipts
app.mount("/api/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

# Include Routers
app.include_router(donors.router, prefix=settings.API_V1_STR)
app.include_router(donations.router, prefix=settings.API_V1_STR)
app.include_router(bank_statement.router, prefix=settings.API_V1_STR)
app.include_router(reconciliation.router, prefix=settings.API_V1_STR)
app.include_router(receipts.router, prefix=settings.API_V1_STR)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "ngo": settings.NGO_NAME,
        "fy": settings.CURRENT_FINANCIAL_YEAR
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
