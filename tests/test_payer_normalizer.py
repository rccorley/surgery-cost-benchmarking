from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from payer_normalizer import (
    _extract_insurer,
    _extract_plan_type,
    fuzzy_match_payer,
    normalize_payer_names,
)


# ── Insurer extraction ──────────────────────────────────────────────

def test_extract_insurer_aetna() -> None:
    assert _extract_insurer("Aetna - All Commercial Plans") == "Aetna"


def test_extract_insurer_aetna_klh() -> None:
    assert _extract_insurer("AETNA - KLH Aetna PPO") == "Aetna"


def test_extract_insurer_premera() -> None:
    assert _extract_insurer("Blue Cross - Premera All Commercial Plans") == "Premera Blue Cross"


def test_extract_insurer_regence() -> None:
    assert _extract_insurer("Blue Shield - Regence All Commercial Plans") == "Regence BlueShield"


def test_extract_insurer_united_variations() -> None:
    assert _extract_insurer("UnitedHealthCare - Medicaid Managed Care Plan") == "UnitedHealthcare"
    assert _extract_insurer("UNITED HEALTHCARE - KLH UHC PPO") == "UnitedHealthcare"


def test_extract_insurer_kaiser() -> None:
    assert _extract_insurer("Kaiser - All Commercial Plans") == "Kaiser Permanente"
    assert _extract_insurer("KAISER PERMANENTE - KLH KAISER PPO") == "Kaiser Permanente"


def test_extract_insurer_molina() -> None:
    assert _extract_insurer("Molina - Exchange") == "Molina Healthcare"
    assert _extract_insurer("Molina Healthcare of WA - Managed Medicaid") == "Molina Healthcare"


def test_extract_insurer_cigna() -> None:
    assert _extract_insurer("CIGNA - KLH CIGNA PPO") == "Cigna"
    assert _extract_insurer("Cigna - All Commercial Plans") == "Cigna"


def test_extract_insurer_coordinated_care() -> None:
    assert _extract_insurer("Coordinated Care - Medicaid Managed Care Plan") == "Coordinated Care"
    assert _extract_insurer("AMBETTER - KLH Coordinated Care Ambetter") == "Coordinated Care"


def test_extract_insurer_self_pay() -> None:
    assert _extract_insurer("DISCOUNTED_CASH") == "Self-Pay / Cash"


def test_extract_insurer_bridgespan_maps_to_regence() -> None:
    assert _extract_insurer("BRIDGESPAN - KLH Regence PPO") == "Regence BlueShield"


def test_extract_insurer_lifewise_maps_to_premera() -> None:
    assert _extract_insurer("Blue Cross - Premera - Lifewise Health Plan") == "Premera Blue Cross"


# ── Plan type extraction ─────────────────────────────────────────────

def test_plan_type_commercial() -> None:
    assert _extract_plan_type("Aetna - All Commercial Plans") == "Commercial"


def test_plan_type_medicare_advantage() -> None:
    assert _extract_plan_type("Kaiser - Medicare Managed Care Plan") == "Medicare Advantage"


def test_plan_type_medicaid() -> None:
    assert _extract_plan_type("Molina - Medicaid Managed Care Plan") == "Medicaid"


def test_plan_type_exchange() -> None:
    assert _extract_plan_type("Molina - Exchange") == "Exchange"


def test_plan_type_ppo() -> None:
    assert _extract_plan_type("CIGNA - KLH CIGNA PPO") == "PPO"


def test_plan_type_hmo() -> None:
    assert _extract_plan_type("Aetna - Gatekeeper Medicare Managed Care - HMO") == "Medicare Advantage"


# ── Normalize full dataframe ─────────────────────────────────────────

def test_normalize_adds_columns() -> None:
    df = pd.DataFrame({"payer_name": ["Aetna - Commercial", "Kaiser - Medicare Managed Care Plan"]})
    out = normalize_payer_names(df)
    assert "payer_group" in out.columns
    assert "payer_canonical" in out.columns
    assert out.iloc[0]["payer_group"] == "Aetna"
    assert out.iloc[1]["payer_group"] == "Kaiser Permanente"
    assert out.iloc[1]["payer_canonical"] == "Kaiser Permanente - Medicare Advantage"


# ── Fuzzy matching ───────────────────────────────────────────────────

def test_fuzzy_match_premera() -> None:
    payers = [
        "Aetna - All Commercial Plans",
        "Blue Cross - Premera All Commercial Plans",
        "Blue Cross - Premera Medicare Managed Care Plan",
        "Cigna - All Commercial Plans",
        "Kaiser - All Commercial Plans",
    ]
    results = fuzzy_match_payer("premera", payers)
    assert len(results) >= 2
    assert all("Premera" in r for r in results)


def test_fuzzy_match_ppo() -> None:
    payers = ["Aetna - PPO", "Cigna - PPO", "Kaiser - HMO", "Regence - PPO"]
    results = fuzzy_match_payer("ppo", payers)
    assert all("PPO" in r for r in results)


def test_fuzzy_match_empty_query() -> None:
    payers = ["A", "B", "C"]
    results = fuzzy_match_payer("", payers)
    assert results == ["A", "B", "C"]


def test_fuzzy_match_no_match() -> None:
    payers = ["Aetna - PPO", "Cigna - HMO"]
    results = fuzzy_match_payer("zzzznotaninsurer", payers)
    assert results == []


def test_fuzzy_match_combined_keywords() -> None:
    payers = [
        "Aetna - All Commercial Plans",
        "Aetna - Medicare Managed Care - PPO",
        "Kaiser - All Commercial Plans",
    ]
    results = fuzzy_match_payer("aetna medicare", payers)
    assert results[0] == "Aetna - Medicare Managed Care - PPO"
