from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LineItem(BaseModel):
    description: str = Field(..., description="Description of the service or product")
    quantity: Optional[float] = Field(default=1.0, description="Quantity")
    unit_price: Optional[float] = Field(default=None, description="Unit price")
    amount: Optional[float] = Field(default=None, description="Total amount for this line")

class InvoiceExtractionResponse(BaseModel):
    vendor_name: str = Field(..., description="Identified vendor or customer organization")
    invoice_id: str = Field(..., description="Invoice, Bill, or Ticket ID")
    invoice_date: str = Field(..., description="Standardized ISO date (YYYY-MM-DD)")
    total_amount: float = Field(..., description="Extracted invoice total")
    currency: str = Field(..., description="Currency code (USD, INR, EUR, GBP, etc.)")
    line_items: List[LineItem] = Field(default_factory=list, description="Array of itemized charges")
    confidence_score: float = Field(..., description="Extraction confidence score from 0.0 to 1.0")
    extraction_engine: str = Field(..., description="Underlying extraction engine utilized")
    raw_text_snippet: Optional[str] = Field(default=None, description="Snippet of raw OCR/PDF text")

class RoutingDecisionRequest(BaseModel):
    total_amount: float
    currency: str
    confidence_score: float

class RoutingDecisionResponse(BaseModel):
    requires_approval: bool
    reason: str
    status: str
    threshold_applied: float

class InvoiceRecord(BaseModel):
    id: Optional[int] = None
    invoice_id: str
    vendor_name: str
    invoice_date: str
    total_amount: float
    currency: str
    status: str
    confidence_score: float
    sender_email: Optional[str] = None
    approval_remarks: Optional[str] = None
    processed_at: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    app_name: str
