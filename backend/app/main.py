from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.database import engine, Base, ensure_db_schema
from backend.app.routers import donors, donations, bank_statement, reconciliation, receipts


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        ensure_db_schema(engine)
    except Exception as e:
        print(f"DB Startup warning: {e}")
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
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploaded screenshots and generated receipts
import os

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(os.path.join(UPLOAD_DIR, "screenshots"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "receipts"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, "statements"), exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/api/uploads", StaticFiles(directory=UPLOAD_DIR), name="api_uploads")

# Include Routers
app.include_router(donors.router, prefix=settings.API_V1_STR)
app.include_router(donations.router, prefix=settings.API_V1_STR)
app.include_router(bank_statement.router, prefix=settings.API_V1_STR)
app.include_router(bank_statement.router, prefix="")
app.include_router(reconciliation.router, prefix=settings.API_V1_STR)
app.include_router(reconciliation.router, prefix="")
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

