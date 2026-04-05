from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import io


def extract_text_with_ocr(pdf_bytes: bytes) -> str:
    """
    Convert PDF pages to images and run OCR.
    Used as fallback when PyMuPDF extracts too little text.
    """
    try:
        images = convert_from_bytes(pdf_bytes)
        full_text = []

        for img in images:
            text = pytesseract.image_to_string(img)
            if text.strip():
                full_text.append(text)

        return "\n".join(full_text)

    except Exception as e:
        print(f"OCR failed for PDF: {e}")
        return ""


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Run OCR directly on a JPG or PNG image.
    Used when user uploads an image file instead of a PDF.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if needed (e.g. RGBA PNG)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        text = pytesseract.image_to_string(image)
        return text.strip()

    except Exception as e:
        print(f"OCR failed for image: {e}")
        return ""