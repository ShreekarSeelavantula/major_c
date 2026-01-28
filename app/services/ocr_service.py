from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image
import io


def extract_text_with_ocr(pdf_bytes: bytes) -> str:
    """
    Convert PDF pages to images and run OCR
    """
    images = convert_from_bytes(pdf_bytes)

    full_text = []

    for page_num, img in enumerate(images):
        text = pytesseract.image_to_string(img)
        full_text.append(text)

    return "\n".join(full_text)
