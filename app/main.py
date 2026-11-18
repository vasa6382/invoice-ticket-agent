import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.models import (
    InvoiceExtractionResponse,
    RoutingDecisionRequest,
    RoutingDecisionResponse,
    InvoiceRecord,
    HealthResponse
)
from app.extractor import InvoiceExtractor
from app.database import (
    init_db,
    save_invoice_record,
    list_invoice_records,
    update_invoice_status
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Automated Invoice & Ticket Processing Agent API (Power Automate Fallback & Direct Processing Engine)",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": f"{settings.APP_NAME} is running. Access /docs for API documentation."}

@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        app_name=settings.APP_NAME
    )

@app.post(
    "/api/v1/extract-invoice",
    response_model=InvoiceExtractionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Extraction"]
)
async def extract_invoice(
    file: UploadFile = File(..., description="Invoice file in PDF, PNG, or JPEG format")
):
    """
    Ingests an uploaded invoice document, extracts structured fields using
    embedded parsing heuristics, and formats the output ready for Power Automate.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing in request.")

    filename_lower = file.filename.lower()
    content = await file.read()

    if not content or len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty attachment received.")

    raw_text = ""
    engine_used = ""

    if filename_lower.endswith(".pdf"):
        raw_text, engine_used = InvoiceExtractor.extract_text_from_pdf(content)
        if len(raw_text.strip()) < 30:
            raw_text, engine_used = InvoiceExtractor.extract_text_from_image(content)
            engine_used = f"{engine_used} (Scanned PDF)"
    elif filename_lower.endswith((".png", ".jpg", ".jpeg", ".tiff")):
        raw_text, engine_used = InvoiceExtractor.extract_text_from_image(content)
    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported document format. Power Automate workflow supports PDF, PNG, and JPEG."
        )

    parsed_result = InvoiceExtractor.parse_invoice_text(raw_text, engine_used)
    return InvoiceExtractionResponse(**parsed_result)

@app.post(
    "/api/v1/evaluate-routing",
    response_model=RoutingDecisionResponse,
    tags=["Business Logic"]
)
async def evaluate_routing(req: RoutingDecisionRequest):
    """
    Replicates the Power Automate business logic:
    Checks financial threshold and confidence scores to determine if human approval is required.
    """
    threshold = settings.THRESHOLD_INR if req.currency.upper() == "INR" else settings.THRESHOLD_USD

    if req.confidence_score < 0.65:
        return RoutingDecisionResponse(
            requires_approval=True,
            reason=f"Low AI extraction confidence ({req.confidence_score * 100:.1f}% < 65%). Manual review mandatory.",
            status="Flagged - Low Confidence",
            threshold_applied=threshold
        )

    if req.total_amount > threshold:
        return RoutingDecisionResponse(
            requires_approval=True,
            reason=f"Amount {req.currency} {req.total_amount:,.2f} exceeds threshold ({req.currency} {threshold:,.2f}). Approval required.",
            status="Pending Approval",
            threshold_applied=threshold
        )

    return RoutingDecisionResponse(
        requires_approval=False,
        reason=f"Amount {req.currency} {req.total_amount:,.2f} is within automated processing limit.",
        status="Auto-Approved",
        threshold_applied=threshold
    )

@app.get("/api/v1/invoices", response_model=List[InvoiceRecord], tags=["Audit Logging"])
async def get_invoices(limit: int = 50):
    """Retrieve processed invoice audit records (mirrors Dataverse records)."""
    return list_invoice_records(limit=limit)

@app.post("/api/v1/invoices/record", response_model=InvoiceRecord, tags=["Audit Logging"])
async def record_invoice(record: InvoiceRecord):
    """Save an invoice entry to the audit log (simulating Dataverse row insertion)."""
    new_id = save_invoice_record(record)
    record.id = new_id
    record.processed_at = datetime.now(timezone.utc).isoformat()
    return record

@app.post("/api/v1/invoices/{invoice_id}/decision", tags=["Human-in-the-Loop"])
async def submit_approval_decision(
    invoice_id: str,
    action: str,
    comments: Optional[str] = "Reviewed via dashboard"
):
    """Simulate Human-in-the-loop Approve or Reject actions."""
    if action.lower() not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

    new_status = "Approved" if action.lower() == "approve" else "Rejected"
    updated = update_invoice_status(invoice_id, new_status, remarks=comments)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found.")

    return {
        "invoice_id": invoice_id,
        "status": new_status,
        "comments": comments,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
