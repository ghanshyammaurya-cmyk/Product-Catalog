import os
import re

from utilities.logger import get_logger

logger = get_logger(__name__)


class PDFValidator:
    """Validates downloaded PDF files."""

    @staticmethod
    def is_valid_pdf(file_path):
        if not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}"

        if not file_path.lower().endswith(".pdf"):
            return False, "File is not a PDF"

        size = os.path.getsize(file_path)
        if size == 0:
            return False, "PDF file is empty"

        with open(file_path, "rb") as handle:
            header = handle.read(5)
        if header != b"%PDF-":
            return False, "Invalid PDF header"

        logger.info("PDF validation passed: %s (%d bytes)", file_path, size)
        return True, "PDF is valid"

    @staticmethod
    def contains_text(file_path, expected_text):
        is_valid, message = PDFValidator.is_valid_pdf(file_path)
        if not is_valid:
            return False, message

        with open(file_path, "rb") as handle:
            content = handle.read().decode("latin-1", errors="ignore")

        pattern = re.escape(str(expected_text))
        if re.search(pattern, content, re.IGNORECASE):
            return True, f"Found text: {expected_text}"

        return False, f"Text not found in PDF: {expected_text}"

    @staticmethod
    def validate(file_path, expected_text=None, min_size_kb=1):
        is_valid, message = PDFValidator.is_valid_pdf(file_path)
        if not is_valid:
            return False, message

        size_kb = os.path.getsize(file_path) / 1024
        if size_kb < min_size_kb:
            return False, f"PDF too small: {size_kb:.1f} KB (min {min_size_kb} KB)"

        if expected_text:
            return PDFValidator.contains_text(file_path, expected_text)

        return True, "PDF validation successful"
