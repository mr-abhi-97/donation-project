import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

# Setup engine with SQLite foreign key enforcement if using SQLite
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_db_schema(target_engine=None):
    """
    Ensures newly added columns exist in the SQLite database without requiring a manual migration tool.
    Safe and idempotent.
    """
    eng = target_engine or engine
    from sqlalchemy import inspect, text
    inspector = inspect(eng)
    if "donations" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("donations")]
        with eng.connect() as conn:
            if "original_transaction_id" not in columns:
                conn.execute(text("ALTER TABLE donations ADD COLUMN original_transaction_id VARCHAR(36)"))
            if "original_transaction_hash" not in columns:
                conn.execute(text("ALTER TABLE donations ADD COLUMN original_transaction_hash VARCHAR(64)"))
            if "duplicate_metadata" not in columns:
                conn.execute(text("ALTER TABLE donations ADD COLUMN duplicate_metadata TEXT"))
            conn.commit()

