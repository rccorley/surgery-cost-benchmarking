"""Insurance document OCR extraction.

Extracts plan benefit parameters (deductible, coinsurance, OOP max) and
billing cycle usage from screenshots of Summary of Benefits (SBC) documents
and Explanation of Benefits (EOB) statements.

Uses EasyOCR for text extraction and regex for structured field parsing.
No Streamlit dependency — this module is independently testable.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import List, Optional

from PIL import Image


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PlanBenefitsExtraction:
    """Fields extracted from a Summary of Benefits document."""

    annual_deductible: Optional[float] = None
    coinsurance_pct: Optional[float] = None  # patient's share, 0-100
    oop_max: Optional[float] = None
    raw_lines: List[str] = field(default_factory=list)

    @property
    def found_any(self) -> bool:
        return any(
            v is not None
            for v in [self.annual_deductible, self.coinsurance_pct, self.oop_max]
        )


@dataclass
class BillingExtraction:
    """Fields extracted from an EOB or billing statement."""

    deductible_total: Optional[float] = None
    deductible_used: Optional[float] = None
    oop_max_total: Optional[float] = None
    oop_spent: Optional[float] = None
    raw_lines: List[str] = field(default_factory=list)

    @property
    def deductible_remaining(self) -> Optional[float]:
        if self.deductible_total is not None and self.deductible_used is not None:
            return max(0.0, self.deductible_total - self.deductible_used)
        return None

    @property
    def oop_max_remaining(self) -> Optional[float]:
        if self.oop_max_total is not None and self.oop_spent is not None:
            return max(0.0, self.oop_max_total - self.oop_spent)
        return None

    @property
    def found_any(self) -> bool:
        return any(
            v is not None
            for v in [
                self.deductible_total,
                self.deductible_used,
                self.oop_max_total,
                self.oop_spent,
            ]
        )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

# Dollar amounts: "$3,000" or "$3000" or "3,000" after a $ sign somewhere
_DOLLAR_RE = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")

# Percentage: "20%" or "20 %"
_PERCENT_RE = re.compile(r"(\d+)\s*%")


def parse_dollar(text: str) -> Optional[float]:
    """Extract the first dollar amount from a string."""
    m = _DOLLAR_RE.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def parse_percent(text: str) -> Optional[float]:
    """Extract the first percentage from a string."""
    m = _PERCENT_RE.search(text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _parse_two_dollars(text: str) -> tuple[Optional[float], Optional[float]]:
    """Extract two dollar amounts from a string like '$1,200 of $3,000'."""
    matches = _DOLLAR_RE.findall(text)
    if len(matches) >= 2:
        try:
            return (
                float(matches[0].replace(",", "")),
                float(matches[1].replace(",", "")),
            )
        except ValueError:
            pass
    return None, None


# ---------------------------------------------------------------------------
# OCR wrapper
# ---------------------------------------------------------------------------

# Lazy-loaded EasyOCR reader (heavy import, ~200MB model on first use)
_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr

        _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _reader


def ocr_image(image_bytes: bytes) -> List[str]:
    """Run OCR on raw image bytes and return list of detected text strings."""
    reader = _get_reader()
    # EasyOCR accepts numpy arrays, PIL images, or file paths
    img = Image.open(io.BytesIO(image_bytes))
    # Convert to RGB if needed (handles RGBA, grayscale, etc.)
    if img.mode != "RGB":
        img = img.convert("RGB")
    import numpy as np

    img_array = np.array(img)
    results = reader.readtext(img_array, detail=0)
    return [str(line).strip() for line in results if str(line).strip()]


# ---------------------------------------------------------------------------
# Plan benefits extraction (from SBC screenshots)
# ---------------------------------------------------------------------------


def extract_plan_benefits_from_lines(lines: List[str]) -> PlanBenefitsExtraction:
    """Parse plan benefit fields from OCR text lines.

    This is separated from OCR so it can be tested independently.
    """
    result = PlanBenefitsExtraction(raw_lines=lines)
    full_text = " ".join(lines).lower()

    # --- Deductible ---
    # Look for lines containing "deductible" with a dollar amount
    for line in lines:
        low = line.lower()
        if "deductible" in low and "out" not in low and "pocket" not in low:
            val = parse_dollar(line)
            if val is not None and val > 0:
                result.annual_deductible = val
                break
    # Fallback: scan full text
    if result.annual_deductible is None:
        m = re.search(
            r"(?:individual\s+)?deductible[^$]*(\$\s?[\d,]+(?:\.\d{2})?)",
            full_text,
        )
        if m:
            result.annual_deductible = parse_dollar(m.group(0))

    # --- Coinsurance ---
    for line in lines:
        low = line.lower()
        if any(kw in low for kw in ["coinsurance", "you pay", "your share", "member pays"]):
            pct = parse_percent(line)
            if pct is not None and 0 < pct <= 100:
                result.coinsurance_pct = pct
                break
    # Fallback: look for "plan pays X%" and invert
    if result.coinsurance_pct is None:
        for line in lines:
            low = line.lower()
            if "plan pays" in low or "insurance pays" in low or "we pay" in low:
                pct = parse_percent(line)
                if pct is not None and 0 < pct <= 100:
                    result.coinsurance_pct = 100.0 - pct
                    break

    # --- Out-of-pocket maximum ---
    for line in lines:
        low = line.lower()
        if any(kw in low for kw in ["out-of-pocket", "out of pocket", "oop", "o.o.p"]):
            val = parse_dollar(line)
            if val is not None and val > 0:
                result.oop_max = val
                break
    # Fallback
    if result.oop_max is None:
        m = re.search(
            r"(?:out.of.pocket|oop)[^$]*(\$\s?[\d,]+(?:\.\d{2})?)",
            full_text,
        )
        if m:
            result.oop_max = parse_dollar(m.group(0))

    return result


def extract_plan_benefits(image_bytes: bytes) -> PlanBenefitsExtraction:
    """Extract plan benefit details from an SBC screenshot."""
    lines = ocr_image(image_bytes)
    return extract_plan_benefits_from_lines(lines)


# ---------------------------------------------------------------------------
# Billing / EOB extraction
# ---------------------------------------------------------------------------


def extract_billing_from_lines(lines: List[str]) -> BillingExtraction:
    """Parse billing/EOB fields from OCR text lines.

    This is separated from OCR so it can be tested independently.
    """
    result = BillingExtraction(raw_lines=lines)
    full_text = " ".join(lines).lower()

    # --- Deductible: "X of Y deductible" or "deductible: X of Y" ---
    for line in lines:
        low = line.lower()
        if "deductible" in low and "out" not in low and "pocket" not in low:
            used, total = _parse_two_dollars(line)
            if used is not None and total is not None:
                # The smaller is usually "used", larger is "total"
                if used > total:
                    used, total = total, used
                result.deductible_used = used
                result.deductible_total = total
                break

    # Fallback: look for "deductible" with "remaining"
    if result.deductible_total is None:
        for line in lines:
            low = line.lower()
            if "deductible" in low and "remain" in low:
                val = parse_dollar(line)
                if val is not None:
                    # We only know the remaining, not total/used
                    # Store as used=0, total=remaining for now
                    result.deductible_used = 0
                    result.deductible_total = val
                    break

    # --- OOP max: "X of Y out-of-pocket" ---
    for line in lines:
        low = line.lower()
        if any(kw in low for kw in ["out-of-pocket", "out of pocket", "oop", "o.o.p"]):
            spent, total = _parse_two_dollars(line)
            if spent is not None and total is not None:
                if spent > total:
                    spent, total = total, spent
                result.oop_spent = spent
                result.oop_max_total = total
                break

    # Fallback: "oop" with "remaining"
    if result.oop_max_total is None:
        for line in lines:
            low = line.lower()
            if ("out-of-pocket" in low or "out of pocket" in low or "oop" in low) and "remain" in low:
                val = parse_dollar(line)
                if val is not None:
                    result.oop_spent = 0
                    result.oop_max_total = val
                    break

    return result


def extract_billing(image_bytes: bytes) -> BillingExtraction:
    """Extract billing/EOB details from a statement screenshot."""
    lines = ocr_image(image_bytes)
    return extract_billing_from_lines(lines)
