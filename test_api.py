import sys
import traceback
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
try:
    resp = client.get("/api/donations")
    print("STATUS_CODE:", resp.status_code)
    if resp.status_code != 200:
        print("ERROR_RESPONSE:", resp.text)
    else:
        print("SUCCESS! Count:", len(resp.json()))
except Exception:
    traceback.print_exc()
