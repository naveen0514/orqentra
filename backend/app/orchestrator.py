"""Intent classification and document text extraction helpers."""
from pathlib import Path


class IntentAgent:
    """Lightweight, explainable classifier. LLM interpretation is optional fallback elsewhere."""
    def run(self, goal: str) -> dict:
        text = goal.lower()
        task = "renewal" if any(x in text for x in ("renew", "renewal", "re-issue", "reissue")) else (
            "registration" if any(x in text for x in ("register", "registration", "incorporate")) else "application"
        )
        categories = [
            ("passport", ("passport",)),
            ("visa_and_travel", ("visa", "immigration", "travel permit")),
            ("scholarship", ("scholarship", "financial aid", "student grant")),
            ("education", ("college", "university", "admission", "school", "course application", "enrol", "enroll")),
            ("employment", ("job", "employment", "career", "recruitment", "resume", "cv application")),
            ("business", ("business", "company", "incorporat", "gst", "trade license", "business license")),
            ("housing", ("rental", "rent application", "housing", "tenancy", "property application")),
            ("public_service", ("government", "certificate", "permit", "license", "licence", "benefit", "public service")),
        ]
        service = next((name for name, words in categories if any(word in text for word in words)), "general_digital_application")
        return {"service": service, "task": task, "original_goal": goal}


class DocumentIntelligenceAgent:
    """Extract searchable text locally; OCR requires a local Tesseract installation."""
    def extract_text(self, path: Path):
        suffix = path.suffix.lower()
        if suffix == ".txt":
            try:
                return path.read_text(errors="ignore"), "plain_text"
            except Exception:
                return "", "failed"
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                if text.strip():
                    return text, "pdf_text_extraction"
                return "", "pdf_scanned_or_no_extractable_text"
            except ImportError:
                return "", "pdf_parser_unavailable_install_pypdf"
            except Exception:
                return "", "pdf_extraction_failed"
        if suffix == ".docx":
            try:
                from docx import Document
                doc = Document(str(path))
                text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                for table in doc.tables:
                    for row in table.rows:
                        text += "\n" + " | ".join(cell.text for cell in row.cells)
                return text, "docx_text_extraction"
            except ImportError:
                return "", "docx_parser_unavailable_install_python_docx"
            except Exception:
                return "", "docx_extraction_failed"
        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            try:
                import pytesseract
                from PIL import Image
                return pytesseract.image_to_string(Image.open(path)), "tesseract_ocr"
            except Exception:
                return "", "ocr_unavailable"
        return "", "unsupported_file_type"
