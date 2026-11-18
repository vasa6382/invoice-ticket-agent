"""
Generates synthetic sample PDF invoices for validation and end-to-end testing.
"""

import os
import pymupdf as fitz

os.makedirs("sample_data", exist_ok=True)

def create_invoice_pdf(filename: str, vendor: str, inv_id: str, date_str: str, items: list, total_str: str):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4 size

    # Background header banner
    rect = fitz.Rect(40, 40, 555, 110)
    page.draw_rect(rect, color=(0.12, 0.16, 0.24), fill=(0.12, 0.16, 0.24))

    # Header texts
    page.insert_text(fitz.Point(60, 75), vendor, fontsize=18, color=(1, 1, 1))
    page.insert_text(fitz.Point(60, 95), "OFFICIAL COMMERCIAL INVOICE", fontsize=10, color=(0.7, 0.75, 0.85))

    page.insert_text(fitz.Point(400, 75), f"Invoice #: {inv_id}", fontsize=12, color=(1, 1, 1))
    page.insert_text(fitz.Point(400, 95), f"Date: {date_str}", fontsize=10, color=(0.8, 0.85, 0.95))

    # Bill To details
    page.insert_text(fitz.Point(60, 150), "BILL TO:", fontsize=11, color=(0.3, 0.3, 0.4))
    page.insert_text(fitz.Point(60, 170), "MissionMind IT Services Private Limited", fontsize=11, color=(0.1, 0.1, 0.1))
    page.insert_text(fitz.Point(60, 185), "Enterprise Automation & Cloud Division", fontsize=9, color=(0.4, 0.4, 0.4))

    # Items table header
    table_header_rect = fitz.Rect(50, 220, 545, 245)
    page.draw_rect(table_header_rect, color=(0.92, 0.94, 0.96), fill=(0.92, 0.94, 0.96))
    page.insert_text(fitz.Point(60, 237), "DESCRIPTION", fontsize=9, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(340, 237), "QTY", fontsize=9, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(420, 237), "UNIT PRICE", fontsize=9, color=(0.2, 0.2, 0.2))
    page.insert_text(fitz.Point(490, 237), "AMOUNT", fontsize=9, color=(0.2, 0.2, 0.2))

    # Items rows
    y = 270
    for desc, qty, rate, amt in items:
        page.insert_text(fitz.Point(60, y), desc, fontsize=10, color=(0.2, 0.2, 0.2))
        page.insert_text(fitz.Point(345, y), str(qty), fontsize=10, color=(0.2, 0.2, 0.2))
        page.insert_text(fitz.Point(420, y), rate, fontsize=10, color=(0.2, 0.2, 0.2))
        page.insert_text(fitz.Point(490, y), amt, fontsize=10, color=(0.2, 0.2, 0.2))
        page.draw_line(fitz.Point(50, y + 8), fitz.Point(545, y + 8), color=(0.9, 0.9, 0.9), width=0.5)
        y += 30

    # Total Box
    total_rect = fitz.Rect(350, y + 20, 545, y + 65)
    page.draw_rect(total_rect, color=(0.95, 0.97, 1.0), fill=(0.95, 0.97, 1.0))
    page.insert_text(fitz.Point(365, y + 48), "TOTAL AMOUNT DUE:", fontsize=10, color=(0.1, 0.1, 0.3))
    page.insert_text(fitz.Point(480, y + 48), total_str, fontsize=12, color=(0.05, 0.1, 0.5))

    # Footer
    page.insert_text(fitz.Point(60, 780), "Thank you for your business. Payment is due within 30 days.", fontsize=8, color=(0.6, 0.6, 0.6))

    filepath = os.path.join("sample_data", filename)
    doc.save(filepath)
    doc.close()
    print(f"Generated sample: {filepath}")

def generate_all_samples():
    # 1. Happy path: Low Value ($450.00)
    create_invoice_pdf(
        "sample_happy_low.pdf",
        "Acme Cloud Solutions Inc.",
        "INV-2026-9812",
        "2026-10-12",
        [
            ("Compute Node Standard Tier 2", 1, "$350.00", "$350.00"),
            ("Data Ingress/Egress Bandwidth", 1, "$100.00", "$100.00")
        ],
        "$450.00 USD"
    )

    # 2. High Value: Requires Approval ($4,850.00)
    create_invoice_pdf(
        "sample_high_val.pdf",
        "Microsoft Corporation",
        "MSFT-AZ-892144",
        "2026-10-11",
        [
            ("Azure OpenAI Dedicated GPT-4o Cluster", 1, "$3500.00", "$3500.00"),
            ("Azure Cosmos DB Multi-Region Active", 1, "$1350.00", "$1350.00")
        ],
        "$4,850.00 USD"
    )

    # 3. INR High Value (₹1,25,000.00)
    create_invoice_pdf(
        "sample_inr_invoice.pdf",
        "Tata Consultancy & Cloud Services Ltd",
        "TCS-BILL-2026-778",
        "2026-10-12",
        [
            ("Managed Automation Infrastructure Service", 1, "₹125000.00", "₹125000.00")
        ],
        "₹1,25,000.00 INR"
    )

    # 4. Corrupted / Low confidence (Missing amounts, blurry placeholder)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(100, 100), "Scan doc - illegible content", fontsize=10, color=(0.8, 0.8, 0.8))
    page.insert_text(fitz.Point(100, 150), "Receipt snippet without clear total or id", fontsize=8, color=(0.85, 0.85, 0.85))
    doc.save("sample_data/sample_low_conf.pdf")
    doc.close()
    print("Generated sample: sample_data/sample_low_conf.pdf")

if __name__ == "__main__":
    generate_all_samples()
