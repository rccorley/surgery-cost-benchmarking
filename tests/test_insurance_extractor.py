"""Tests for insurance document OCR extraction.

These tests exercise the regex parsing logic WITHOUT calling EasyOCR,
by testing extract_*_from_lines() which accepts pre-parsed text lines.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.insurance_extractor import (
    BillingExtraction,
    PlanBenefitsExtraction,
    extract_billing_from_lines,
    extract_plan_benefits_from_lines,
    parse_dollar,
    parse_percent,
)


# ── Dollar parsing ─────────────────────────────────────────────────


def test_parse_dollar_simple() -> None:
    assert parse_dollar("$3,000") == 3000.0


def test_parse_dollar_no_comma() -> None:
    assert parse_dollar("$500") == 500.0


def test_parse_dollar_with_cents() -> None:
    assert parse_dollar("$1,234.56") == 1234.56


def test_parse_dollar_with_space() -> None:
    assert parse_dollar("$ 2,500") == 2500.0


def test_parse_dollar_in_sentence() -> None:
    assert parse_dollar("Your deductible is $3,000 per year") == 3000.0


def test_parse_dollar_none_when_missing() -> None:
    assert parse_dollar("No amount here") is None


def test_parse_dollar_large_amount() -> None:
    assert parse_dollar("$125,000") == 125000.0


# ── Percent parsing ────────────────────────────────────────────────


def test_parse_percent_simple() -> None:
    assert parse_percent("20%") == 20.0


def test_parse_percent_with_space() -> None:
    assert parse_percent("20 %") == 20.0


def test_parse_percent_in_sentence() -> None:
    assert parse_percent("You pay 30% after deductible") == 30.0


def test_parse_percent_none_when_missing() -> None:
    assert parse_percent("No percent here") is None


# ── Plan benefits extraction ───────────────────────────────────────


def test_extract_plan_standard_sbc() -> None:
    """Standard SBC layout with all three fields."""
    lines = [
        "Summary of Benefits and Coverage",
        "Individual Deductible $3,000",
        "Coinsurance 20%",
        "Out-of-Pocket Maximum $8,000",
    ]
    result = extract_plan_benefits_from_lines(lines)
    assert result.annual_deductible == 3000.0
    assert result.coinsurance_pct == 20.0
    assert result.oop_max == 8000.0
    assert result.found_any is True


def test_extract_plan_alternate_wording() -> None:
    """Different wording for coinsurance and OOP."""
    lines = [
        "Your Plan Benefits",
        "Annual Deductible: $2,500",
        "You pay 30% of allowed amount",
        "Out of Pocket Limit: $6,500",
    ]
    result = extract_plan_benefits_from_lines(lines)
    assert result.annual_deductible == 2500.0
    assert result.coinsurance_pct == 30.0
    assert result.oop_max == 6500.0


def test_extract_plan_plan_pays_inverted() -> None:
    """When document says 'plan pays 80%', infer patient pays 20%."""
    lines = [
        "Deductible $1,500",
        "Plan pays 80%",
        "OOP Maximum $5,000",
    ]
    result = extract_plan_benefits_from_lines(lines)
    assert result.coinsurance_pct == 20.0


def test_extract_plan_partial() -> None:
    """Only some fields can be extracted."""
    lines = [
        "Benefits Summary",
        "Annual Deductible: $4,000",
        "Some other text about coverage",
    ]
    result = extract_plan_benefits_from_lines(lines)
    assert result.annual_deductible == 4000.0
    assert result.coinsurance_pct is None
    assert result.oop_max is None
    assert result.found_any is True


def test_extract_plan_nothing_found() -> None:
    """No recognizable insurance fields."""
    lines = ["Hello world", "This is a random document"]
    result = extract_plan_benefits_from_lines(lines)
    assert result.found_any is False


def test_extract_plan_member_pays() -> None:
    """'Member pays' phrasing."""
    lines = [
        "Deductible $2,000",
        "Member pays 25%",
        "Out-of-pocket max $7,000",
    ]
    result = extract_plan_benefits_from_lines(lines)
    assert result.coinsurance_pct == 25.0


# ── Billing / EOB extraction ──────────────────────────────────────


def test_extract_billing_x_of_y_deductible() -> None:
    """Standard '$X of $Y deductible met' pattern."""
    lines = [
        "Your Benefits Summary",
        "$1,200 of $3,000 deductible met",
        "$2,500 of $8,000 out-of-pocket maximum met",
    ]
    result = extract_billing_from_lines(lines)
    assert result.deductible_used == 1200.0
    assert result.deductible_total == 3000.0
    assert result.deductible_remaining == 1800.0
    assert result.oop_spent == 2500.0
    assert result.oop_max_total == 8000.0
    assert result.oop_max_remaining == 5500.0


def test_extract_billing_remaining_pattern() -> None:
    """'$X deductible remaining' pattern."""
    lines = [
        "Deductible remaining: $1,500",
    ]
    result = extract_billing_from_lines(lines)
    # When only remaining is given, we store total=remaining, used=0
    assert result.deductible_remaining == 1500.0


def test_extract_billing_partial() -> None:
    """Only deductible info available."""
    lines = [
        "$500 of $2,000 deductible",
        "Other stuff here",
    ]
    result = extract_billing_from_lines(lines)
    assert result.deductible_used == 500.0
    assert result.deductible_total == 2000.0
    assert result.oop_max_total is None
    assert result.oop_spent is None
    assert result.found_any is True


def test_extract_billing_nothing_found() -> None:
    lines = ["Some random text", "No billing info"]
    result = extract_billing_from_lines(lines)
    assert result.found_any is False


def test_billing_remaining_properties() -> None:
    """Test the computed properties directly."""
    b = BillingExtraction(
        deductible_total=5000, deductible_used=2000,
        oop_max_total=10000, oop_spent=4000,
    )
    assert b.deductible_remaining == 3000.0
    assert b.oop_max_remaining == 6000.0


def test_billing_remaining_none_when_missing() -> None:
    b = BillingExtraction(deductible_total=5000)
    assert b.deductible_remaining is None


def test_billing_remaining_floors_at_zero() -> None:
    """Can't have negative remaining."""
    b = BillingExtraction(deductible_total=1000, deductible_used=2000)
    assert b.deductible_remaining == 0.0


def test_extract_billing_swaps_if_needed() -> None:
    """If amounts come in wrong order (larger first), they get swapped."""
    lines = [
        "Deductible: $5,000 of $1,500 applied",
    ]
    result = extract_billing_from_lines(lines)
    assert result.deductible_used == 1500.0
    assert result.deductible_total == 5000.0
