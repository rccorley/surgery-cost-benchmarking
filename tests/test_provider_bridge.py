from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.external.provider_bridge import build_provider_hospital_bridge


def test_build_provider_hospital_bridge(tmp_path: Path) -> None:
    year_dir = tmp_path / "2023"
    year_dir.mkdir(parents=True)
    src = year_dir / "Facility_Affiliation.csv"
    pd.DataFrame(
        {
            "NPI": ["1111111111"],
            "org_pac_id": ["22222"],
            "facility_name": ["PeaceHealth St. Joseph Medical Center"],
        }
    ).to_csv(src, index=False)

    out = build_provider_hospital_bridge(tmp_path, 2023)
    assert not out.empty
    assert set(out["entity_type"].astype(str)) == {"clinician", "group"}
    assert "peacehealth st. joseph medical center" in set(out["hospital_name_std"].astype(str))
