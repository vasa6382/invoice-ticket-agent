"""
Generates the Invoices_Tracker.xlsx file with professional styling and column schemas
ready for Excel Online (Business) connector in Power Automate.
"""

import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_excel_tracker(output_path: str = "Invoices_Tracker.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices_Processed"

    # Header columns matching Power Automate schema
    headers = [
        "InvoiceID",
        "VendorName",
        "InvoiceDate",
        "TotalAmount",
        "Currency",
        "Status",
        "ConfidenceScore",
        "SenderEmail",
        "ApprovalRemarks",
        "ProcessedAt"
    ]

    ws.append(headers)

    # Sample rows
    sample_rows = [
        [
            "INV-2026-9812",
            "Acme Cloud Solutions Inc.",
            "2026-10-12",
            450.00,
            "USD",
            "Auto-Approved",
            0.95,
            "billing@acmecloud.com",
            "Auto-approved: under $1,000 threshold",
            "2026-10-12 14:32:00"
        ],
        [
            "MSFT-AZ-892144",
            "Microsoft Corporation",
            "2026-10-11",
            4850.00,
            "USD",
            "Approved",
            0.92,
            "azure-invoices@microsoft.com",
            "Approved by Finance Manager via Teams",
            "2026-10-11 16:15:20"
        ],
        [
            "TCS-BILL-2026-778",
            "Tata Consultancy & Cloud Services Ltd",
            "2026-10-12",
            125000.00,
            "INR",
            "Approved",
            0.90,
            "finance@tcs.com",
            "Approved via Outlook Approval card",
            "2026-10-12 18:05:44"
        ]
    ]

    for row in sample_rows:
        ws.append(row)

    # Styles
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    border_thin = Border(
        left=Side(style='thin', color='E5E7EB'),
        right=Side(style='thin', color='E5E7EB'),
        top=Side(style='thin', color='E5E7EB'),
        bottom=Side(style='thin', color='E5E7EB')
    )

    # Style Header
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Style Data rows
    for row_idx in range(2, len(sample_rows) + 2):
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = border_thin
            if col_idx == 4:  # TotalAmount
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal="right")
            elif col_idx in [3, 7, 10]:  # Dates
                cell.alignment = Alignment(horizontal="center")

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val = str(cell.value or "")
            if len(val) > max_len:
                max_len = len(val)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(output_path)
    print(f"Excel Tracker created successfully at: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    build_excel_tracker()
