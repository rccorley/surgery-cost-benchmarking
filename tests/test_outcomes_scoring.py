from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.features.outcomes_scoring import (
    reliability_weight,
    normalize_measure_score,
    build_mips_outcomes_features,
)


def test_reliability_weight_bounds() -> None:
    assert reliability_weight(0) == 0.0
    assert reliability_weight(25) == 0.5
    assert reliability_weight(50) == 1.0
    assert reliability_weight(500) == 1.0


def test_directionality_normalization() -> None:
    assert normalize_measure_score(80, "higher_better") == 80
    assert normalize_measure_score(80, "lower_better") == 20


def test_build_mips_outcomes_features_basic() -> None:
    raw = pd.DataFrame(
        {
            "year": [2023, 2023, 2023, 2023],
            "entity_type": ["clinician", "clinician", "clinician", "clinician"],
            "entity_id": ["1", "2", "1", "2"],
            "measure_cd": ["A", "A", "B", "B"],
            "measure_title": ["Readmission Rate", "Readmission Rate", "Outcome Improvement", "Outcome Improvement"],
            "measure_domain": ["READMISSION", "READMISSION", "OUTCOME_OTHER", "OUTCOME_OTHER"],
            "raw_rate": [10.0, 20.0, 70.0, 60.0],
            "patient_count": [60, 60, 60, 60],
            "directionality": ["lower_better", "lower_better", "higher_better", "higher_better"],
        }
    )

    out = build_mips_outcomes_features(raw)
    assert not out.empty
    assert {"outcomes_composite", "outcomes_confidence", "measure_score_norm"}.issubset(set(out.columns))
    assert set(out["outcomes_confidence"].astype(str)) == {"HIGH"}
