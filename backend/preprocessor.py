"""
Preprocessor module for the CS-CME engine.

Handles:
  - Text cleaning
  - PDF text extraction
  - Sentence segmentation
  - Input validation & truncation
"""

import re
import io
from typing import List, Tuple

import spacy

from utils import MAX_PDF_PAGES, validate_input, truncate_text


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, List[str]]:
    """
    Extract text from PDF bytes.

    Returns
    -------
    text : str
        Full extracted text.
    warnings : list[str]
        Any warnings (e.g. page-limit exceeded).
    """
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return "", ["PyPDF2 is not installed. Cannot process PDF files."]

    warnings: List[str] = []
    reader = PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)

    if total_pages > MAX_PDF_PAGES:
        warnings.append(
            f"PDF has {total_pages} pages; only the first "
            f"{MAX_PDF_PAGES} will be processed."
        )

    pages_to_read = min(total_pages, MAX_PDF_PAGES)
    text_parts: List[str] = []
    for i in range(pages_to_read):
        page_text = reader.pages[i].extract_text()
        if page_text:
            text_parts.append(page_text)

    return "\n".join(text_parts), warnings


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Basic cleaning: normalise whitespace, fix common artefacts."""
    # Replace common PDF artefacts
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse multiple blank lines into two newlines (paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Strip each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


# ---------------------------------------------------------------------------
# Sentence segmentation
# ---------------------------------------------------------------------------

def segment_sentences(text: str, nlp: spacy.language.Language) -> List[str]:
    """
    Split *text* into sentences using spaCy's sentence boundary detector.
    """
    doc = nlp(text)
    sentences: List[str] = []
    for sent in doc.sents:
        s = sent.text.strip()
        if s:
            sentences.append(s)
    return sentences


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess(raw_text: str, nlp: spacy.language.Language):
    """
    Full preprocessing pipeline.

    Returns
    -------
    dict with keys:
        sentences : list[str]
        cleaned_text : str
        warnings : list[str]
    """
    validation = validate_input(raw_text)
    warnings = validation.get("warnings", [])

    text = truncate_text(raw_text)
    text = clean_text(text)
    sentences = segment_sentences(text, nlp)

    return {
        "sentences": sentences,
        "cleaned_text": text,
        "warnings": warnings,
    }
