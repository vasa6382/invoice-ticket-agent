import os
import pytest
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_extract_happy_low_value():
    pdf_path = "sample_data/sample_happy_low.pdf"
    assert os.path.exists(pdf_path)

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/extract-invoice",
            files={"file": ("sample_happy_low.pdf", f, "application/pdf")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "Acme" in data["vendor_name"]
    assert "INV-2026-9812" in data["invoice_id"]
    assert data["total_amount"] == 450.00
    assert data["currency"] == "USD"
    assert data["confidence_score"] >= 0.70

    # Test routing rule
    route_res = client.post(
        "/api/v1/evaluate-routing",
        json={
            "total_amount": data["total_amount"],
            "currency": data["currency"],
            "confidence_score": data["confidence_score"]
        }
    )
    assert route_res.status_code == 200
    route_data = route_res.json()
    assert route_data["requires_approval"] is False
    assert route_data["status"] == "Auto-Approved"

def test_extract_high_value_approval_flow():
    pdf_path = "sample_data/sample_high_val.pdf"
    assert os.path.exists(pdf_path)

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/extract-invoice",
            files={"file": ("sample_high_val.pdf", f, "application/pdf")}
        )

    assert response.status_code == 200
    data = response.json()
    assert "Microsoft" in data["vendor_name"]
    assert "MSFT-AZ-892144" in data["invoice_id"]
    assert data["total_amount"] == 4850.00
    assert data["currency"] == "USD"

    # Test routing rule (> $1000)
    route_res = client.post(
        "/api/v1/evaluate-routing",
        json={
            "total_amount": data["total_amount"],
            "currency": data["currency"],
            "confidence_score": data["confidence_score"]
        }
    )
    assert route_res.status_code == 200
    route_data = route_res.json()
    assert route_data["requires_approval"] is True
    assert route_data["status"] == "Pending Approval"

def test_extract_inr_high_value_flow():
    pdf_path = "sample_data/sample_inr_invoice.pdf"
    assert os.path.exists(pdf_path)

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/extract-invoice",
            files={"file": ("sample_inr_invoice.pdf", f, "application/pdf")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_amount"] == 125000.00
    assert data["currency"] == "INR"

    # Test routing rule (> ₹50,000)
    route_res = client.post(
        "/api/v1/evaluate-routing",
        json={
            "total_amount": data["total_amount"],
            "currency": data["currency"],
            "confidence_score": data["confidence_score"]
        }
    )
    assert route_res.status_code == 200
    route_data = route_res.json()
    assert route_data["requires_approval"] is True

def test_extract_low_confidence():
    pdf_path = "sample_data/sample_low_conf.pdf"
    assert os.path.exists(pdf_path)

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/extract-invoice",
            files={"file": ("sample_low_conf.pdf", f, "application/pdf")}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["confidence_score"] < 0.65

    # Test routing rule: flags due to low confidence
    route_res = client.post(
        "/api/v1/evaluate-routing",
        json={
            "total_amount": data["total_amount"],
            "currency": data["currency"],
            "confidence_score": data["confidence_score"]
        }
    )
    assert route_res.status_code == 200
    route_data = route_res.json()
    assert route_data["requires_approval"] is True
    assert "Low Confidence" in route_data["status"]

def test_save_and_retrieve_audit_record():
    payload = {
        "invoice_id": "TEST-INV-100",
        "vendor_name": "Test Vendor LLC",
        "invoice_date": "2026-10-13",
        "total_amount": 99.00,
        "currency": "USD",
        "status": "Auto-Approved",
        "confidence_score": 0.95,
        "sender_email": "billing@testvendor.com",
        "approval_remarks": "Test run"
    }

    create_res = client.post("/api/v1/invoices/record", json=payload)
    assert create_res.status_code == 200
    rec = create_res.json()
    assert rec["id"] is not None

    list_res = client.get("/api/v1/invoices?limit=10")
    assert list_res.status_code == 200
    invoices = list_res.json()
    assert len(invoices) > 0
    assert any(inv["invoice_id"] == "TEST-INV-100" for inv in invoices)
