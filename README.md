# Enterprise Automated Invoice & Ticket Processing Agent

An enterprise-grade automation solution integrating **Microsoft Power Automate**, **AI Builder (Invoice & Receipt Prebuilt Model)**, **Microsoft Dataverse / Excel Online**, and **Office 365 Outlook**, paired with an embedded **Python FastAPI Fallback Engine & Interactive Testing Sandbox**.

---

## 🏗️ Architecture & Component Overview

```
Inbound Email (Outlook 365)
       │
       ▼
[Trigger Filter: Has Attachments & Subject (Invoice|Bill|Service Request)]
       │
       ▼
[Attachment Filter: Skip Signatures / Icons, Only PDF/PNG/JPG > 10KB]
       │
       ▼
[AI Builder: Extract information from invoices / Fallback REST Engine]
       │
       ▼
[WDL Sanitization: Total Amount, Date, Vendor, Currency, Confidence]
       │
       ├──────────────────────────────────────────┐
       │                                          │
[Amount <= Threshold ($1,000 / ₹50k)]     [Amount > Threshold OR Conf < 0.65]
       │                                          │
       │                                   [Approvals V2: Teams / Outlook Card]
       │                                          │
       │                                    ┌─────┴──────────┐
       │                                    ▼                ▼
       │                              [Approved]        [Rejected]
       │                                    │                │
       ▼                                    ▼                ▼
[Dataverse / Excel: Add Row]          [Dataverse]    [Notify Sender Email]
       │
       ▼
[Scope Catch Error Boundary: Admin Alert on Failure]
```

---

## 📁 Repository Structure

```
automate/
├── app/
│   ├── config.py                 # Thresholds ($1,000 / ₹50k) and API settings
│   ├── database.py               # SQLite audit persistence mirroring Dataverse
│   ├── extractor.py              # PyMuPDF + pypdf + heuristic regex parser
│   ├── main.py                   # FastAPI REST API & dashboard router
│   ├── models.py                 # Pydantic schemas (Extraction, Routing, Audit)
│   └── static/
│       ├── app.js                # Interactive sandbox dashboard logic
│       ├── index.html            # Dark-mode glassmorphic test console
│       └── styles.css            # Modern styling, tokens, and micro-animations
├── power_automate/
│   ├── invoice_processing_flow.json  # Importable Power Automate flow JSON
│   └── workflow_expressions.md       # Exact WDL expressions & step configurations
├── dataverse/
│   └── Invoices_Processed_Entity.json # Dataverse entity schema
├── scripts/
│   ├── create_excel_tracker.py       # Generates Invoices_Tracker.xlsx
│   └── generate_sample_invoices.py   # Generates 4 realistic test PDF invoices
├── sample_data/                      # Test PDFs for all 4 test cases
│   ├── sample_happy_low.pdf          # $450.00 (Auto-approved)
│   ├── sample_high_val.pdf           # $4,850.00 (Pending Approval)
│   ├── sample_inr_invoice.pdf        # ₹1,25,000.00 (Pending Approval)
│   └── sample_low_conf.pdf           # Low confidence (Flagged)
├── tests/
│   └── test_extraction.py            # Automated pytest validation suite
├── Invoices_Tracker.xlsx             # Pre-configured Excel Online Tracker
├── Dockerfile                        # Production container specification
├── docker-compose.yml                # Microservice composition
├── requirements.txt                  # Python dependencies
└── README.md                         # Project documentation
```

---

## 🚀 Quickstart: Running the Interactive Sandbox

Launch the local server to inspect the dashboard, test invoice uploads, and simulate approvals:

```bash
uvicorn app.main:app --reload --port 8000
```

1. Open your browser to `http://localhost:8000`.
2. **Drag & drop** any invoice PDF or click the **Pre-built Test Cases**:
   - `1. Low Value ($450)` -> Evaluates to **Auto-Approved**.
   - `2. High Value ($4,850)` -> Evaluates to **Pending Approval**.
   - `3. INR Invoice (₹125,000)` -> Evaluates to **Pending Approval**.
   - `4. Blurry / Missing Total` -> Evaluates to **Flagged (Low Confidence)**.
3. Simulate human approvals (`✓ Approve` / `✕ Reject`) and view the synced audit trail under the **Dataverse / Audit Records** tab.
4. Access interactive API documentation at `http://localhost:8000/docs`.

---

## ⚡ Power Automate Setup & Deployment

1. **Trigger Setup**:
   - Open Power Automate and create an **Automated cloud flow**.
   - Select `When a new email arrives (V3)` from **Office 365 Outlook**.
   - Under Settings > Trigger Conditions, paste:
     ```text
     @and(greater(length(triggerOutputs()?['body/attachments']), 0), or(contains(toLower(triggerOutputs()?['body/subject']), 'invoice'), contains(toLower(triggerOutputs()?['body/subject']), 'bill'), contains(toLower(triggerOutputs()?['body/subject']), 'service request')))
     ```
2. **Document Processing**:
   - Add `Apply to each` on `triggerOutputs()?['body/attachments']`.
   - Add condition to skip signatures and files under 10KB.
   - Add `Get Attachment (V2)`.
   - Add `AI Builder` -> `Extract information from invoices` (or use the HTTP action calling `POST http://<your-host>:8000/api/v1/extract-invoice`).
3. **Data Cleaning Expressions**:
   - Refer to [`power_automate/workflow_expressions.md`](power_automate/workflow_expressions.md) for expressions handling currency stripping, decimal parsing, and ISO date conversion.
4. **Data Persistence**:
   - Add `Microsoft Dataverse` -> `Add a new row` into `cr_invoices_processed`, or
   - Add `Excel Online (Business)` -> `Add a row into a table` using [`Invoices_Tracker.xlsx`](Invoices_Tracker.xlsx).

---

## 🧪 Automated Testing

Execute the test suite validating extraction, routing rules, thresholds, and audit logging:

```bash
python -m pytest tests/ -v
```

All 6 test cases validate deterministically:
* `test_health_check`: Validates API availability and uptime metadata.
* `test_extract_happy_low_value`: Tests sub-threshold invoice ($450.00) auto-approval.
* `test_extract_high_value_approval_flow`: Tests high-value USD invoice ($4,850.00) routing to approval.
* `test_extract_inr_high_value_flow`: Tests high-value INR invoice (₹125,000.00) routing to approval.
* `test_extract_low_confidence`: Tests low-confidence/illegible document flagging (< 65%).
* `test_save_and_retrieve_audit_record`: Validates Dataverse-mirrored audit table insertions.

python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

python -m app.main
uvicorn app.main:app --reload

