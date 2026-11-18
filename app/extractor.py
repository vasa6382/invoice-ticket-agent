import io
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from PIL import Image

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from pypdf import PdfReader
from app.models import LineItem

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "₹": "INR",
    "£": "GBP",
    "¥": "JPY",
    "USD": "USD",
    "INR": "INR",
    "RS.": "INR",
    "RS": "INR",
    "EUR": "EUR",
    "GBP": "GBP",
    "CAD": "CAD",
    "AUD": "AUD",
}

class InvoiceExtractor:
    """Robust extraction engine supporting PDFs and image-based invoices."""

    @staticmethod
    def extract_text_from_pdf(content: bytes) -> Tuple[str, str]:
        """Extracts text using PyMuPDF (fitz) or pypdf fallback."""
        text = ""
        engine = "PyMuPDF"

        if fitz:
            try:
                doc = fitz.open(stream=content, filetype="pdf")
                for page in doc:
                    text += page.get_text() + "\n"
                doc.close()
                if text.strip():
                    return text, engine
            except Exception:
                pass

        # Fallback to pypdf
        try:
            reader = PdfReader(io.BytesIO(content))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            engine = "pypdf"
        except Exception as e:
            raise ValueError(f"Unable to read PDF file: {str(e)}")

        return text, engine

    @staticmethod
    def extract_text_from_image(content: bytes) -> Tuple[str, str]:
        """Extracts text from images using PyMuPDF OCR or basic image handling."""
        try:
            img = Image.open(io.BytesIO(content))
            if fitz and hasattr(fitz, "open"):
                try:
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format=img.format or "PNG")
                    doc = fitz.open(stream=img_byte_arr.getvalue(), filetype="image")
                    text = ""
                    for page in doc:
                        text += page.get_text()
                    doc.close()
                    if text.strip():
                        return text, "PyMuPDF-Image"
                except Exception:
                    pass
        except Exception as e:
            raise ValueError(f"Invalid image format: {str(e)}")

        return "", "PIL-Image"

    @classmethod
    def parse_invoice_text(cls, raw_text: str, engine_used: str) -> Dict[str, Any]:
        """Applies intelligent regex and heuristic pattern matching to text."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        
        # 1. Vendor Name Heuristic
        vendor_name = cls._extract_vendor(lines)
        
        # 2. Invoice ID
        invoice_id, id_confidence = cls._extract_invoice_id(raw_text)
        
        # 3. Invoice Date
        invoice_date, date_confidence = cls._extract_date(raw_text)
        
        # 4. Total Amount & Currency
        total_amount, currency, amount_confidence = cls._extract_total_and_currency(raw_text)
        
        # 5. Line items
        line_items = cls._extract_line_items(lines, total_amount)
        
        # 6. Overall Confidence Calculation
        weights = [
            1.0 if vendor_name != "Unknown Vendor" else 0.4,
            id_confidence,
            date_confidence,
            amount_confidence
        ]
        confidence_score = round(sum(weights) / len(weights), 4)

        return {
            "vendor_name": vendor_name,
            "invoice_id": invoice_id,
            "invoice_date": invoice_date,
            "total_amount": total_amount,
            "currency": currency,
            "line_items": line_items,
            "confidence_score": confidence_score,
            "extraction_engine": engine_used,
            "raw_text_snippet": raw_text[:400].strip() if raw_text else "No text extracted"
        }

    @staticmethod
    def _extract_vendor(lines: List[str]) -> str:
        vendor_signals = ["inc", "llc", "ltd", "corp", "corporation", "technologies", "services", "solutions", "labs", "systems", "gmbh"]
        
        # Check first 8 lines
        for line in lines[:8]:
            clean = line.lower()
            if any(signal in clean for signal in vendor_signals):
                return line.strip()
                
        # Second pass: pick the first line that is not a generic header
        blacklist = ["invoice", "bill", "tax invoice", "statement", "receipt", "purchase order", "po", "original", "duplicate", "official", "commercial"]
        for line in lines[:5]:
            clean = line.lower()
            if not any(b in clean for b in blacklist) and len(line) >= 3 and not line.startswith(("#", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
                return line.strip()

        return "Unknown Vendor"

    @staticmethod
    def _extract_invoice_id(raw_text: str) -> Tuple[str, float]:
        # High confidence patterns with prefix like INV-, BILL-, or label with #/no/number
        patterns = [
            r"\b(INV-[0-9A-Za-z\-]+)\b",
            r"\b(BILL-[0-9A-Za-z\-]+)\b",
            r"(?:invoice|bill|ticket)\s*(?:#|no\.?|number|id|code)\s*[:\-]?\s*([A-Za-z0-9\-_]{3,25})",
            r"(?:invoice|bill|ticket)\s*[:\-]\s*([A-Za-z0-9\-_]{3,25})",
            r"\b([A-Z]{2,5}-[A-Z0-9\-]{3,20})\b"
        ]
        invalid_words = {"invoice", "date", "due", "total", "amount", "usd", "inr", "bill", "ticket", "commercial", "official", "true", "false"}

        for pattern in patterns:
            for match in re.finditer(pattern, raw_text, re.IGNORECASE):
                val = match.group(1).strip()
                if val.lower() not in invalid_words and len(val) >= 3:
                    # Prefer values containing at least one digit
                    if any(c.isdigit() for c in val):
                        return val, 0.95
                    return val, 0.85

        # Fallback generated ID
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"GEN-{timestamp}", 0.30

    @staticmethod
    def _extract_date(raw_text: str) -> Tuple[str, float]:
        patterns = [
            (r"(?:date|dated|issue date)[\s:]*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})", "%Y-%m-%d"),
            (r"(?:date|dated|issue date)[\s:]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{4})", None),
            (r"\b([0-9]{4}[-/][0-9]{2}[-/][0-9]{2})\b", "%Y-%m-%d"),
            (r"\b([0-9]{2}[-/][0-9]{2}[-/][0-9]{4})\b", None)
        ]

        for pattern, _ in patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip().replace("/", "-")
                try:
                    if re.match(r"^\d{4}-\d{1,2}-\d{1,2}$", date_str):
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                        return dt.strftime("%Y-%m-%d"), 0.95
                    elif re.match(r"^\d{1,2}-\d{1,2}-\d{4}$", date_str):
                        parts = date_str.split("-")
                        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                        if day > 12 and month <= 12:
                            dt = datetime(year, month, day)
                        else:
                            dt = datetime(year, int(parts[0]), int(parts[1]))
                        return dt.strftime("%Y-%m-%d"), 0.90
                except Exception:
                    pass
                return date_str, 0.70

        return datetime.now(timezone.utc).strftime("%Y-%m-%d"), 0.40

    @classmethod
    def _extract_total_and_currency(cls, raw_text: str) -> Tuple[float, str, float]:
        currency = "USD"
        
        # Check text for currency signals
        upper_text = raw_text.upper()
        if "INR" in upper_text or "₹" in raw_text or "RS." in upper_text or "RS " in upper_text or "RUPEES" in upper_text:
            currency = "INR"
        elif "EUR" in upper_text or "€" in raw_text:
            currency = "EUR"
        elif "GBP" in upper_text or "£" in raw_text:
            currency = "GBP"
        elif "CAD" in upper_text:
            currency = "CAD"
        elif "AUD" in upper_text:
            currency = "AUD"

        patterns = [
            # TOTAL AMOUNT DUE: \n $450.00 USD or INR 1,25,000.00 or 1,25,000.00 INR
            r"(?:grand\s+total|total\s+amount\s+due|total\s+amount|amount\s+due|balance\s+due|total\s+payable|total)[\s:\n]*([$€₹£¥]|USD|INR|Rs\.?|\ufffd)?\s*([\d,]+\.?\d*)\s*(USD|INR|EUR|GBP)?",
            r"([$€₹£¥]|USD|INR|Rs\.?|\ufffd)\s*([\d,]+\.?\d*)\s*(?:total|due)",
            r"([\d,]+\.?\d*)\s*(?:USD|INR|EUR|GBP)"
        ]

        amounts_found = []
        for pattern in patterns:
            for match in re.finditer(pattern, raw_text, re.IGNORECASE):
                groups = match.groups()
                # Find the numeric portion
                num_str = None
                curr_indicator = None
                for g in groups:
                    if g:
                        cleaned = g.strip()
                        if re.match(r"^[\d,]+\.?\d*$", cleaned) and any(c.isdigit() for c in cleaned):
                            num_str = cleaned
                        elif cleaned.upper() in CURRENCY_SYMBOLS:
                            curr_indicator = CURRENCY_SYMBOLS[cleaned.upper()]

                if num_str:
                    clean_num = num_str.replace(",", "")
                    try:
                        val = float(clean_num)
                        if val > 0:
                            chosen_curr = curr_indicator or currency
                            amounts_found.append((val, chosen_curr))
                    except ValueError:
                        continue

        if amounts_found:
            chosen_amount, detected_currency = max(amounts_found, key=lambda x: x[0])
            return chosen_amount, detected_currency, 0.95

        return 0.0, currency, 0.20

    @staticmethod
    def _extract_line_items(lines: List[str], total_amount: float) -> List[LineItem]:
        items: List[LineItem] = []
        line_item_pattern = re.compile(r"^([A-Za-z0-9\s\-_.,#()]+?)\s+(\d+(?:\.\d+)?)\s+([$€₹£\ufffd]?\s*[\d,]+(?:\.\d{2})?)\s+([$€₹£\ufffd]?\s*[\d,]+(?:\.\d{2})?)$")
        simple_pattern = re.compile(r"^([A-Za-z0-9\s\-_.,#()]{3,40})\s+([$€₹£\ufffd]?\s*[\d,]+(?:\.\d{2})?)$")

        for line in lines:
            if any(term in line.lower() for term in ["total", "subtotal", "tax", "vat", "gst", "amount due"]):
                continue

            match = line_item_pattern.match(line)
            if match:
                desc = match.group(1).strip()
                qty = float(match.group(2))
                rate_str = re.sub(r"[$€₹£\ufffd,]", "", match.group(3)).strip()
                amt_str = re.sub(r"[$€₹£\ufffd,]", "", match.group(4)).strip()
                try:
                    items.append(LineItem(
                        description=desc,
                        quantity=qty,
                        unit_price=float(rate_str),
                        amount=float(amt_str)
                    ))
                    continue
                except ValueError:
                    pass

            simple_match = simple_pattern.match(line)
            if simple_match:
                desc = simple_match.group(1).strip()
                amt_str = re.sub(r"[$€₹£\ufffd,]", "", simple_match.group(2)).strip()
                try:
                    amt = float(amt_str)
                    if amt > 0 and amt != total_amount:
                        items.append(LineItem(description=desc, quantity=1.0, unit_price=amt, amount=amt))
                except ValueError:
                    pass

        if not items:
            items.append(LineItem(
                description="Professional Services / General Invoice Items",
                quantity=1.0,
                unit_price=total_amount,
                amount=total_amount
            ))

        return items
