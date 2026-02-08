import fitz
from io import BytesIO


def extract_text_from_pdf(file_bytes: bytes, max_pages: int | None = None) -> str:
    text = []

    with fitz.open(stream=BytesIO(file_bytes), filetype="pdf") as doc:
        page_count = len(doc)
        pages_to_read = page_count if max_pages is None else min(max_pages, page_count)

        for i in range(pages_to_read):
            page = doc[i]
            page_text = page.get_text()
            if page_text:
                text.append(page_text)

    return "\n".join(text).strip()
