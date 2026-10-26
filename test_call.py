import sys
import traceback
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))

from backend.app.database import SessionLocal
from backend.app.routers.donations import list_donations

db = SessionLocal()
try:
    print("Calling list_donations(db=db)...")
    res = list_donations(db=db)
    print("Direct call succeeded! Count:", len(res))
    
    # Now let's test pydantic serialization of the result
    from backend.app.schemas import DonationResponse
    serialized = [DonationResponse.model_validate(r).model_dump() for r in res]
    print("Serialization succeeded! Count:", len(serialized))
except Exception:
    traceback.print_exc()
finally:
    db.close()
