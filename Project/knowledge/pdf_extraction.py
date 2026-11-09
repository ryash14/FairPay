"""Gets the text out of the PDFs and does nothing else with it."""
import os

from pypdf import PdfReader


def extract_text_from_directory(docs_directory):
    """Every .pdf in the folder, in file-name order, read once in strict mode."""
    entries = []
    for file_name in sorted(os.listdir(docs_directory)):
        if not file_name.lower().endswith(".pdf"):
            continue
        reader = PdfReader(os.path.join(docs_directory, file_name), strict=True)
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if not text.strip():
                raise ValueError(f"{file_name} has a page from which no text can be extracted")
            pages.append(text)
        entries.append({"document_name": file_name, "document_text": "\n".join(pages)})
    return entries
