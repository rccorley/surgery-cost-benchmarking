from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patient_estimator import (
    BenefitDesign,
    EpisodeEstimate,
    FeeComponents,
    PatientEstimate,
    compare_hospitals,
    compare_payers,
    estimate_episode_cost,
    estimate_patient_cost,
    get_episode_components,
    procedure_label,
)


def _benefit(deductible: float = 2000, coins: float = 0.20, oop: float = 6000) -> BenefitDesign:
    return BenefitDesign(
        deductible_remaining=deductible,
        coinsurance_pct=coins,
        oop_max_remaining=oop,
    )


# ── Core waterfall logic ───────────────────────────────────────────


def test_basic_waterfall() -> None:
    """Standard case: deductible + coinsurance, below OOP max."""
    est = estimate_patient_cost(10_000, _benefit(2000, 0.20, 6000))
    # Deductible: 2000, coinsurance: 20% of 8000 = 1600, total = 3600
    assert est.deductible_portion == 2000.0
    assert est.coinsurance_portion == 1600.0
    assert est.patient_total == 3600.0
    assert est.plan_pays == 6400.0
    assert est.hit_oop_max is False


def test_hits_oop_max() -> None:
    """Patient cost exceeds OOP max, so it gets capped."""
    est = estimate_patient_cost(100_000, _benefit(5000, 0.30, 8000))
    # Raw: 5000 + 0.30 * 95000 = 5000 + 28500 = 33500 > 8000
    assert est.patient_total == 8000.0
    assert est.plan_pays == 92_000.0
    assert est.hit_oop_max is True


def test_zero_deductible() -> None:
    """Deductible already met -- all goes through coinsurance."""
    est = estimate_patient_cost(20_000, _benefit(0, 0.20, 10000))
    # Deductible: 0, coinsurance: 20% of 20000 = 4000
    assert est.deductible_portion == 0.0
    assert est.coinsurance_portion == 4000.0
    assert est.patient_total == 4000.0


def test_zero_coinsurance() -> None:
    """No coinsurance -- patient pays deductible only."""
    est = estimate_patient_cost(20_000, _benefit(3000, 0.0, 10000))
    assert est.deductible_portion == 3000.0
    assert est.coinsurance_portion == 0.0
    assert est.patient_total == 3000.0


def test_negotiated_rate_less_than_deductible() -> None:
    """Rate is below the remaining deductible."""
    est = estimate_patient_cost(500, _benefit(2000, 0.20, 6000))
    assert est.deductible_portion == 500.0
    assert est.coinsurance_portion == 0.0
    assert est.patient_total == 500.0
    assert est.plan_pays == 0.0


def test_zero_rate() -> None:
    est = estimate_patient_cost(0, _benefit())
    assert est.patient_total == 0.0


def test_negative_rate() -> None:
    est = estimate_patient_cost(-100, _benefit())
    assert est.patient_total == 0.0


def test_deductible_equals_oop_max() -> None:
    """Edge: deductible remaining == OOP max remaining."""
    est = estimate_patient_cost(10_000, _benefit(5000, 0.20, 5000))
    # Raw: 5000 + 0.20*5000 = 6000, capped at 5000
    assert est.patient_total == 5000.0
    assert est.hit_oop_max is True


# ── Procedure labels ───────────────────────────────────────────────


def test_known_code_gets_friendly_label() -> None:
    assert procedure_label("27447") == "Total Knee Replacement"


def test_unknown_code_falls_back_to_description() -> None:
    assert procedure_label("99999", "Custom Procedure") == "Custom Procedure"


def test_unknown_code_no_description() -> None:
    assert procedure_label("99999") == "Procedure 99999"


# ── Comparison helpers ─────────────────────────────────────────────


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "hospital_name": ["H1", "H1", "H1", "H2", "H2"],
            "payer_name": ["Aetna", "Regence", "Molina", "Aetna", "Regence"],
            "code": ["27447", "27447", "27447", "27447", "27447"],
            "code_type": ["CPT", "CPT", "CPT", "CPT", "CPT"],
            "description": ["Knee", "Knee", "Knee", "Knee", "Knee"],
            "effective_price": [20000.0, 50000.0, 15000.0, 18000.0, 45000.0],
            "procedure_label": ["Total Knee Replacement"] * 5,
        }
    )


def test_compare_payers_returns_sorted() -> None:
    df = _sample_df()
    result = compare_payers(df, "H1", "27447", _benefit())
    assert len(result) == 3
    # Should be sorted by your_estimated_cost ascending
    costs = result["your_estimated_cost"].tolist()
    assert costs == sorted(costs)


def test_compare_hospitals_returns_sorted() -> None:
    df = _sample_df()
    result = compare_hospitals(df, "Aetna", "27447", _benefit())
    assert len(result) == 2
    costs = result["your_estimated_cost"].tolist()
    assert costs == sorted(costs)


def test_compare_payers_empty_when_no_match() -> None:
    df = _sample_df()
    result = compare_payers(df, "Nonexistent", "27447", _benefit())
    assert result.empty


def test_compare_hospitals_empty_when_no_match() -> None:
    df = _sample_df()
    result = compare_hospitals(df, "Nonexistent", "27447", _benefit())
    assert result.empty


# ── Episode cost estimation ───────────────────────────────────────


def test_episode_cost_joint_replacement() -> None:
    """DRG 470 joint replacement: facility fee + small add-ons."""
    ep = estimate_episode_cost(20_000.0, "470")
    assert ep.facility_fee == 20_000.0
    assert ep.surgeon_fee == 2_100.0  # 10.5%
    assert ep.anesthesia_fee == 1_600.0  # 8%
    assert ep.pathology_lab_fee == 40.0  # 0.2%
    assert ep.imaging_fee == 160.0  # 0.8%
    assert ep.total_episode == 23_900.0
    assert ep.is_default is False
    assert "Joint Replacement" in ep.category


def test_episode_cost_general_surgery() -> None:
    """CPT 47562 cholecystectomy: larger professional fee proportion."""
    ep = estimate_episode_cost(5_000.0, "47562")
    assert ep.facility_fee == 5_000.0
    assert ep.surgeon_fee == 2_000.0  # 40%
    assert ep.anesthesia_fee == 750.0  # 15%
    assert ep.total_episode == 8_000.0
    assert "General Surgery" in ep.category


def test_episode_cost_gi_endoscopy() -> None:
    """CPT 45378 colonoscopy: professional fee is large relative to facility."""
    ep = estimate_episode_cost(1_000.0, "45378")
    assert ep.surgeon_fee == 550.0  # 55%
    assert ep.anesthesia_fee == 300.0  # 30%
    assert ep.pathology_lab_fee == 100.0  # 10%
    assert ep.total_episode == 1_950.0


def test_episode_cost_zero_rate() -> None:
    ep = estimate_episode_cost(0, "470")
    assert ep.total_episode == 0
    assert ep.surgeon_fee == 0


def test_episode_cost_negative_rate() -> None:
    ep = estimate_episode_cost(-500, "470")
    assert ep.total_episode == 0


def test_episode_cost_unknown_code_uses_default() -> None:
    ep = estimate_episode_cost(10_000.0, "99999")
    assert ep.is_default is True
    assert ep.surgeon_fee == 2_000.0  # 20% default
    assert ep.total_episode == 13_400.0  # 1.34x


def test_get_episode_components_known() -> None:
    comp = get_episode_components("470")
    assert comp.surgeon == 0.105
    assert comp.total_multiplier > 1.0


def test_get_episode_components_unknown() -> None:
    comp = get_episode_components("XXXXX")
    assert comp.category == "Estimated (Default)"


def test_fee_components_total_multiplier() -> None:
    comp = FeeComponents(surgeon=0.10, anesthesia=0.05, pathology_lab=0.02, imaging=0.01)
    assert abs(comp.total_multiplier - 1.18) < 0.001


def test_episode_cost_spinal_fusion() -> None:
    ep = estimate_episode_cost(25_000.0, "473")
    assert ep.surgeon_fee == 3_000.0  # 12%
    assert ep.anesthesia_fee == 2_500.0  # 10%
    assert "Spinal Fusion" in ep.category
