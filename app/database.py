import sqlite3
from datetime import datetime, timezone
from typing import List, Optional
from app.config import settings
from app.models import InvoiceRecord

def get_db_connection():
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices_processed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL,
            vendor_name TEXT NOT NULL,
            invoice_date TEXT NOT NULL,
            total_amount REAL NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            sender_email TEXT,
            approval_remarks TEXT,
            processed_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Auto-initialize database schema on module load
init_db()

def save_invoice_record(record: InvoiceRecord) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO invoices_processed (
            invoice_id, vendor_name, invoice_date, total_amount,
            currency, status, confidence_score, sender_email,
            approval_remarks, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record.invoice_id,
        record.vendor_name,
        record.invoice_date,
        record.total_amount,
        record.currency,
        record.status,
        record.confidence_score,
        record.sender_email,
        record.approval_remarks,
        now_str
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def list_invoice_records(limit: int = 50) -> List[InvoiceRecord]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM invoices_processed ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        results.append(InvoiceRecord(
            id=row["id"],
            invoice_id=row["invoice_id"],
            vendor_name=row["vendor_name"],
            invoice_date=row["invoice_date"],
            total_amount=row["total_amount"],
            currency=row["currency"],
            status=row["status"],
            confidence_score=row["confidence_score"],
            sender_email=row["sender_email"],
            approval_remarks=row["approval_remarks"],
            processed_at=row["processed_at"]
        ))
    return results

def update_invoice_status(invoice_id: str, new_status: str, remarks: Optional[str] = None) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE invoices_processed
        SET status = ?, approval_remarks = ?
        WHERE invoice_id = ?
    """, (new_status, remarks, invoice_id))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0
