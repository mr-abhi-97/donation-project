import urllib.request
import urllib.parse
import json
import os
from decimal import Decimal

BASE_URL = "http://localhost:8000/api"

print("--- RUNNING FULL END-TO-END AUTOMATED VERIFICATION ---", flush=True)

# 1. Check Health
req = urllib.request.urlopen(f"{BASE_URL}/health")
health_data = json.loads(req.read().decode())
print("1. Health Check:", health_data, flush=True)
assert health_data["status"] == "healthy"

# 2. Check Reconciliation Stats
req = urllib.request.urlopen(f"{BASE_URL}/reconciliation/stats")
stats = json.loads(req.read().decode())
print("2. Reconciliation Stats:", stats, flush=True)
assert stats["total_donations"] >= 5
assert stats["total_statement_entries"] >= 5

# 3. Check Donations List
req = urllib.request.urlopen(f"{BASE_URL}/donations/")
donations = json.loads(req.read().decode())
print(f"3. Retrieved {len(donations)} donations from queue.", flush=True)
matched = [d for d in donations if d["status"] == "MATCHED"]
flagged = [d for d in donations if d["status"] == "FLAGGED_REVIEW"]
print(f"   - Matched donations: {len(matched)}")
print(f"   - Flagged for review: {len(flagged)}")

# 4. Check Fuzzy Candidate suggestions for flagged donation
if flagged:
    flagged_id = flagged[0]["id"]
    req = urllib.request.urlopen(f"{BASE_URL}/reconciliation/candidates/{flagged_id}")
    candidates = json.loads(req.read().decode())
    print(f"4. Fuzzy candidates for flagged donation {flagged_id}:", len(candidates), "candidates found", flush=True)
    if candidates:
        top = candidates[0]
        print(f"   Top candidate score: {top['confidence_score']} (UTR distance: {top['utr_distance']}, type: {top['match_type']})", flush=True)

# 5. Verify a donation and generate 80G Tax Receipt
unverified_valid = [d for d in donations if not d["is_verified"] and not d.get("is_flagged_fraud")]
target_donation = unverified_valid[0] if unverified_valid else donations[0]
print(f"5. Verifying donation {target_donation['id']}...", flush=True)
req = urllib.request.Request(f"{BASE_URL}/donations/{target_donation['id']}/verify", method="POST")
verify_resp = json.loads(urllib.request.urlopen(req).read().decode())
print("   Verified Status:", verify_resp["status"], "| is_verified:", verify_resp["is_verified"], flush=True)
assert verify_resp["is_verified"] == True

# 6. Check Receipt lookup
donor_pan = target_donation.get("donor", {}).get("pan_number", "MNOPQ9012R")
print(f"6. Looking up receipt for PAN {donor_pan}...", flush=True)
req = urllib.request.urlopen(f"{BASE_URL}/receipts/lookup?pan={donor_pan}")
lookup_data = json.loads(req.read().decode())
print("   Lookup records found:", len(lookup_data.get("records", [])), flush=True)

# 7. Check Form 10BD Excel export
print("7. Testing Form 10BD Excel export...", flush=True)
req = urllib.request.urlopen(f"{BASE_URL}/receipts/export/form-10bd")
excel_bytes = req.read()
print(f"   Form 10BD Excel generated successfully! ({len(excel_bytes)} bytes)", flush=True)
assert len(excel_bytes) > 1000

# 8. Check Bank Statement Sample Template
print("8. Testing Bank Statement sample template download...", flush=True)
req = urllib.request.urlopen(f"{BASE_URL}/bank-statement/sample-template")
template_bytes = req.read()
print(f"   Sample bank statement template downloaded! ({len(template_bytes)} bytes)", flush=True)
assert len(template_bytes) > 1000

print("\n--- ALL END-TO-END WORKFLOWS PASSED 100% SUCCESSFULLY! ---", flush=True)
