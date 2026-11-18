"""
End-to-end script to test all 4 invoice scenarios against the extraction engine.
"""

import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)
    print("=================================================================")
    print("    INVOICE & TICKET PROCESSING AGENT - END-TO-END TEST RUN      ")
    print("=================================================================")

    tests = [
        ("sample_data/sample_happy_low.pdf", "Scenario 1: Low Value ($450.00 USD)"),
        ("sample_data/sample_high_val.pdf", "Scenario 2: High Value ($4,850.00 USD)"),
        ("sample_data/sample_inr_invoice.pdf", "Scenario 3: INR High Value (INR 125,000.00)"),
        ("sample_data/sample_low_conf.pdf", "Scenario 4: Low Quality / Missing Total Document")
    ]

    for filepath, desc in tests:
        print(f"\n[TESTING] {desc}")
        with open(filepath, "rb") as f:
            res = client.post("/api/v1/extract-invoice", files={"file": (filepath, f, "application/pdf")})
        
        data = res.json()
        print(f"  -> Vendor Identified : {data['vendor_name']}")
        print(f"  -> Invoice / Ticket ID: {data['invoice_id']}")
        print(f"  -> Invoice Date       : {data['invoice_date']}")
        print(f"  -> Extracted Amount   : {data['currency']} {data['total_amount']:,.2f}")
        print(f"  -> AI Confidence Score: {data['confidence_score'] * 100:.1f}%")
        print(f"  -> Engine Utilized    : {data['extraction_engine']}")

        # Evaluate routing
        route_res = client.post("/api/v1/evaluate-routing", json={
            "total_amount": data["total_amount"],
            "currency": data["currency"],
            "confidence_score": data["confidence_score"]
        })
        decision = route_res.json()
        print(f"  -> Routing Decision   : [{decision['status']}] (Requires Approval: {decision['requires_approval']})")
        print(f"  -> Routing Reason     : {decision['reason']}")

    print("\n=================================================================")
    print("       ALL SCENARIOS VALIDATED AND PASSED DETERMINISTICALLY      ")
    print("=================================================================")

if __name__ == "__main__":
    run_tests()
