"""
PII (Personally Identifiable Information) Redaction Pipeline.

Uses a multi-layer approach:
  1. Fast regex patterns to catch common PII (emails, phone numbers, SSNs, credit cards).
  2. Optional: presidio-analyzer for deep NLP-based NER detection (if installed).

This module intercepts text BEFORE it is chunked and stored in ChromaDB or
sent to any third-party LLM API, ensuring enterprise SOC2 compliance.
"""
import re
import logging
from typing import Tuple

logger = logging.getLogger("processpilot.pii")

# ===== REGEX-BASED PII PATTERNS =====
_PII_PATTERNS = [
    # Email addresses
    (re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b'), "[REDACTED_EMAIL]"),
    # US Social Security Numbers (SSN)
    (re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'), "[REDACTED_SSN]"),
    # Phone numbers (US and international variants)
    (re.compile(r'(\+?\d{1,3}[\s\-]?)?(\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4})'), "[REDACTED_PHONE]"),
    # Credit/Debit Card Numbers (Visa, MasterCard, Amex, Discover)
    (re.compile(r'\b(?:\d[ -]?){13,16}\b'), "[REDACTED_CARD]"),
    # IP Addresses
    (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), "[REDACTED_IP]"),
    # Passport numbers (generic alphanumeric 6-9 chars)
    (re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'), "[REDACTED_PASSPORT]"),
    # Dates of birth pattern (DOB: MM/DD/YYYY or DD-MM-YYYY)
    (re.compile(r'\b(DOB|Date of Birth|D\.O\.B)[:\s]+\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b', re.IGNORECASE), "[REDACTED_DOB]"),
]

# ===== OPTIONAL: Deep NER using Microsoft Presidio =====
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    _presidio_analyzer = AnalyzerEngine()
    _presidio_anonymizer = AnonymizerEngine()
    HAS_PRESIDIO = True
    logger.info("[PII] Presidio NLP engine loaded — deep NER redaction active.")
except ImportError:
    HAS_PRESIDIO = False
    logger.info("[PII] Presidio not installed — using regex-only redaction. Install with: pip install presidio-analyzer presidio-anonymizer")


def redact_pii(text: str) -> Tuple[str, int]:
    """
    Redact PII from the given text.
    Returns:
        (redacted_text, count_of_redactions)
    """
    if not text:
        return text, 0

    redaction_count = 0

    # Layer 1: Presidio deep NER (if available)
    if HAS_PRESIDIO:
        try:
            results = _presidio_analyzer.analyze(text=text, language="en")
            if results:
                redacted = _presidio_anonymizer.anonymize(text=text, analyzer_results=results)
                text = redacted.text
                redaction_count += len(results)
                logger.debug(f"[PII] Presidio redacted {len(results)} entities.")
        except Exception as e:
            logger.warning(f"[PII] Presidio failed, falling back to regex: {e}")

    # Layer 2: Fast regex patterns (always run as backstop)
    for pattern, replacement in _PII_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            text = pattern.sub(replacement, text)
            redaction_count += len(matches)

    if redaction_count > 0:
        logger.info(f"[PII] Redacted {redaction_count} PII entities from document chunk.")

    return text, redaction_count


def redact_document(full_text: str) -> Tuple[str, int]:
    """
    Run PII redaction on an entire document's extracted text before chunking.
    This is the main entry point called by ingestion.py.
    """
    redacted_text, total_redactions = redact_pii(full_text)
    if total_redactions > 0:
        logger.info(f"[PII] Document redaction complete: {total_redactions} total PII entities removed.")
    return redacted_text, total_redactions
