from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.benchmark import (
    _infer_hospital_name_from_source,
    _flatten_cms_v3_flat,
    filter_scope,
    ingest_with_audit,
    run,
    with_hospital_rank,
    flatten_peacehealth_wide,
    payer_dispersion,
    flatten_standard_charge_information,
    procedure_confidence,
)


def test_filter_scope_basic(tmp_path: Path) -> None:
    prices = pd.DataFrame(
        {
            "hospital_name": ["PeaceHealth St. Joseph Medical Center", "Other Hospital"],
            "code": ["27447", "27447"],
            "code_type": ["CPT", "CPT"],
            "description": ["SOURCE DESC", "ignored"],
            "effective_price": [25000.0, 18000.0],
        }
    )

    h = tmp_path / "h.csv"
    p = tmp_path / "p.csv"
    pd.DataFrame({"hospital_name": ["PeaceHealth St. Joseph Medical Center"]}).to_csv(h, index=False)
    pd.DataFrame(
        {"code": ["27447"], "code_type": ["CPT"], "description": ["Total knee arthroplasty"]}
    ).to_csv(p, index=False)

    out = filter_scope(prices, h, p)
    assert len(out) == 1
    assert out.iloc[0]["description"] == "Total knee arthroplasty"


def test_focus_rank_returns_focus_only() -> None:
    scoped = pd.DataFrame(
        {
            "hospital_name": ["PeaceHealth St. Joseph Medical Center", "Skagit Valley Hospital"],
            "code": ["27447", "27447"],
            "description": ["Total knee arthroplasty", "Total knee arthroplasty"],
            "effective_price": [30000.0, 25000.0],
        }
    )
    out = with_hospital_rank(scoped, "PeaceHealth St. Joseph Medical Center")
    assert len(out) == 1
    assert out.iloc[0]["rank_low_to_high"] == 2.0


def test_flatten_peacehealth_wide_extracts_payer_and_cash() -> None:
    wide = pd.DataFrame(
        {
            "description": ["Test Proc"],
            "code|1": ["27130"],
            "code|1|type": ["CPT"],
            "standard_charge|discounted_cash": [1000.0],
            "standard_charge|Aetna Health|Commercial|negotiated_dollar": [1200.0],
        }
    )
    out = flatten_peacehealth_wide(wide)
    assert len(out) == 2
    assert set(out["payer_name"].astype(str)) == {"DISCOUNTED_CASH", "Aetna Health - Commercial"}


def test_flatten_peacehealth_wide_estimated_amount_fallback() -> None:
    """Payers with only estimated_amount (no negotiated_dollar) should be included."""
    wide = pd.DataFrame(
        {
            "description": ["Test Proc"],
            "code|1": ["470"],
            "code|1|type": ["MS-DRG"],
            "standard_charge|discounted_cash": [1000.0],
            "standard_charge|Aetna|Commercial|negotiated_dollar": [1200.0],
            "estimated_amount|Cigna|Commercial": [1500.0],
        }
    )
    out = flatten_peacehealth_wide(wide)
    payers = set(out["payer_name"].astype(str))
    assert "DISCOUNTED_CASH" in payers
    assert "Aetna - Commercial" in payers
    assert "Cigna - Commercial" in payers
    assert len(out) == 3


def test_flatten_peacehealth_wide_estimated_amount_no_duplicate() -> None:
    """When a payer has both negotiated_dollar AND estimated_amount, only use negotiated_dollar."""
    wide = pd.DataFrame(
        {
            "description": ["Test Proc"],
            "code|1": ["470"],
            "code|1|type": ["MS-DRG"],
            "standard_charge|Aetna|Commercial|negotiated_dollar": [1200.0],
            "estimated_amount|Aetna|Commercial": [1500.0],
        }
    )
    out = flatten_peacehealth_wide(wide)
    aetna = out[out["payer_name"] == "Aetna - Commercial"]
    assert len(aetna) == 1
    assert float(aetna.iloc[0]["negotiated_rate"]) == 1200.0


def test_payer_dispersion_includes_unique_payer_count() -> None:
    scoped = pd.DataFrame(
        {
            "hospital_name": ["PeaceHealth", "PeaceHealth", "PeaceHealth"],
            "code": ["27130", "27130", "27130"],
            "description": ["Hip", "Hip", "Hip"],
            "effective_price": [1000.0, 1200.0, 1400.0],
            "payer_name": ["Aetna", "Regence", "DISCOUNTED_CASH"],
        }
    )
    out = payer_dispersion(scoped)
    assert len(out) == 1
    assert out.iloc[0]["n_unique_payers"] == 3
    assert out.iloc[0]["p90_p10_ratio"] > 1


def test_filter_scope_rejects_wrong_code_type(tmp_path: Path) -> None:
    prices = pd.DataFrame(
        {
            "hospital_name": ["PeaceHealth St. Joseph Medical Center"],
            "code": ["27447"],
            "code_type": ["LOCAL"],
            "effective_price": [1000.0],
        }
    )
    h = tmp_path / "h.csv"
    p = tmp_path / "p.csv"
    pd.DataFrame({"hospital_name": ["PeaceHealth St. Joseph Medical Center"]}).to_csv(h, index=False)
    pd.DataFrame({"code": ["27447"], "code_type": ["CPT"]}).to_csv(p, index=False)
    out = filter_scope(prices, h, p)
    assert out.empty


def test_flatten_standard_charge_information_reads_payers_information() -> None:
    payload = {
        "hospital_name": "Test Hospital",
        "standard_charge_information": [
            {
                "description": "Test Procedure",
                "code_information": [{"code": "27130", "type": "CPT"}],
                "standard_charges": [
                    {
                        "discounted_cash": 1000.0,
                        "gross_charge": 5000.0,
                        "setting": "outpatient",
                        "payers_information": [
                            {
                                "payer_name": "Aetna",
                                "plan_name": "Commercial",
                                "estimated_amount": 1200.0,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    out = flatten_standard_charge_information(payload)
    assert len(out) == 2
    assert "DISCOUNTED_CASH" in set(out["payer_name"].astype(str))
    assert "Aetna - Commercial" in set(out["payer_name"].astype(str))
    # gross_charge and setting should propagate to all rows
    assert (out["gross_charge"] == 5000.0).all()
    assert (out["setting"] == "outpatient").all()


def test_flatten_standard_charge_information_captures_drg_min_max() -> None:
    """DRG inpatient charges use minimum/maximum for de-identified min/max rates."""
    payload = {
        "hospital_name": "Test Hospital",
        "standard_charge_information": [
            {
                "description": "Hip Replacement",
                "code_information": [{"code": "470", "type": "MS-DRG"}],
                "standard_charges": [
                    {
                        "minimum": 15000.0,
                        "maximum": 45000.0,
                        "setting": "inpatient",
                        "payers_information": [
                            {
                                "payer_name": "Premera",
                                "plan_name": "PPO",
                                "estimated_amount": 28000.0,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    out = flatten_standard_charge_information(payload)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["charge_min"] == 15000.0
    assert row["charge_max"] == 45000.0
    assert row["setting"] == "inpatient"
    assert row["negotiated_rate"] == 28000.0


def test_flatten_standard_charge_information_missing_optional_fields() -> None:
    """When gross_charge, setting, minimum, maximum are absent, rows still parse correctly."""
    payload = {
        "hospital_name": "Test Hospital",
        "standard_charge_information": [
            {
                "description": "Simple Procedure",
                "code_information": [{"code": "99213", "type": "CPT"}],
                "standard_charges": [
                    {
                        "payers_information": [
                            {
                                "payer_name": "Aetna",
                                "plan_name": "PPO",
                                "negotiated_dollar": 150.0,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    out = flatten_standard_charge_information(payload)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["negotiated_rate"] == 150.0
    assert "gross_charge" not in out.columns or pd.isna(row.get("gross_charge"))
    assert "setting" not in out.columns or pd.isna(row.get("setting"))
    assert "charge_min" not in out.columns or pd.isna(row.get("charge_min"))
    assert "charge_max" not in out.columns or pd.isna(row.get("charge_max"))


def test_flatten_standard_charge_preserves_zero_dollar_rate() -> None:
    """A $0 negotiated rate should be preserved, not skipped by the or-chain."""
    payload = {
        "hospital_name": "Test Hospital",
        "standard_charge_information": [
            {
                "description": "Zero Dollar Procedure",
                "code_information": [{"code": "99211", "type": "CPT"}],
                "standard_charges": [
                    {
                        "payers_information": [
                            {
                                "payer_name": "Medicaid",
                                "plan_name": "State",
                                "negotiated_dollar": 0.0,
                                "estimated_amount": 500.0,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    out = flatten_standard_charge_information(payload)
    assert len(out) == 1
    # Should use negotiated_dollar (0.0), NOT fall through to estimated_amount (500.0)
    assert out.iloc[0]["negotiated_rate"] == 0.0


def test_flatten_standard_charge_empty_string_falls_through() -> None:
    """Empty-string negotiated_dollar should fall through to estimated_amount."""
    payload = {
        "hospital_name": "Test Hospital",
        "standard_charge_information": [
            {
                "description": "Empty String Procedure",
                "code_information": [{"code": "27447", "type": "CPT"}],
                "standard_charges": [
                    {
                        "payers_information": [
                            {
                                "payer_name": "BlueCross",
                                "plan_name": "PPO",
                                "negotiated_dollar": "",
                                "estimated_amount": 12500.0,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    out = flatten_standard_charge_information(payload)
    assert len(out) == 1
    # Empty string should be treated as missing → use estimated_amount
    assert out.iloc[0]["negotiated_rate"] == 12500.0


def test_infer_hospital_name_peacehealth_united_general() -> None:
    """PeaceHealth United General files should map to the correct hospital name."""
    assert _infer_hospital_name_from_source(
        "data/raw/peacehealth_united_general_mrf_unzipped/standardcharges.csv",
        pd.NA,
    ) == "PeaceHealth United General Hospital"


def test_infer_hospital_name_uw_medical_center() -> None:
    assert _infer_hospital_name_from_source(
        "data/raw/uw_medical_center_standardcharges.json",
        pd.NA,
    ) == "UW Medical Center"


def test_infer_hospital_name_harborview() -> None:
    assert _infer_hospital_name_from_source(
        "data/raw/harborview_standardcharges.json",
        pd.NA,
    ) == "Harborview Medical Center"


def test_infer_hospital_name_evergreenhealth() -> None:
    assert _infer_hospital_name_from_source(
        "data/raw/evergreenhealth_standardcharges.csv",
        pd.NA,
    ) == "EvergreenHealth Medical Center"


def test_infer_hospital_name_skagit_valley() -> None:
    assert _infer_hospital_name_from_source(
        "data/raw/skagit_valley_standardcharges.csv",
        pd.NA,
    ) == "Skagit Valley Hospital"


def test_infer_hospital_name_cascade_valley() -> None:
    assert _infer_hospital_name_from_source(
        "data/raw/cascade_valley_standardcharges.csv",
        pd.NA,
    ) == "Cascade Valley Hospital"


def test_infer_hospital_name_overlake() -> None:
    assert _infer_hospital_name_from_source(
        "data/raw/overlake_standardcharges.csv",
        pd.NA,
    ) == "Overlake Medical Center"


def test_infer_hospital_peacehealth_before_united_general() -> None:
    """Generic peacehealth path (without united_general) should map to St. Joseph."""
    assert _infer_hospital_name_from_source(
        "data/raw/peacehealth_st_joseph_mrf_unzipped/standardcharges.csv",
        pd.NA,
    ) == "PeaceHealth St Joseph Medical Center"


def test_flatten_cms_v3_flat_extracts_payer_and_rate() -> None:
    """CMS v3.0 flat format with payer_name/plan_name as regular columns."""
    flat = pd.DataFrame(
        {
            "description": ["Hip Replacement", "Hip Replacement"],
            "code|1": ["27130", "27130"],
            "code|1|type": ["CPT", "CPT"],
            "standard_charge|gross": [50000.0, 50000.0],
            "standard_charge|discounted_cash": [30000.0, 30000.0],
            "payer_name": ["Aetna", "Regence"],
            "plan_name": ["PPO", "Blue Shield"],
            "standard_charge|negotiated_dollar": [25000.0, 28000.0],
            "estimated_amount": [pd.NA, pd.NA],
        }
    )
    out = _flatten_cms_v3_flat(flat)
    assert len(out) == 2
    assert set(out["payer_name"]) == {"Aetna - PPO", "Regence - Blue Shield"}
    assert set(out["negotiated_rate"]) == {25000.0, 28000.0}
    assert out.iloc[0]["cash_price"] == 30000.0


def test_flatten_cms_v3_flat_estimated_amount_fallback() -> None:
    """CMS v3.0 flat format should fall back to estimated_amount when negotiated_dollar is missing."""
    flat = pd.DataFrame(
        {
            "description": ["Knee Replacement"],
            "code|1": ["27447"],
            "code|1|type": ["CPT"],
            "standard_charge|discounted_cash": [35000.0],
            "payer_name": ["Cigna"],
            "plan_name": ["HMO"],
            "standard_charge|negotiated_dollar": [pd.NA],
            "estimated_amount": [32000.0],
        }
    )
    out = _flatten_cms_v3_flat(flat)
    assert len(out) == 1
    assert float(out.iloc[0]["negotiated_rate"]) == 32000.0


def test_procedure_confidence_labels_low_for_single_hospital() -> None:
    scoped = pd.DataFrame(
        {
            "hospital_name": ["A", "A", "A"],
            "code": ["27130", "27130", "27130"],
            "code_type": ["CPT", "CPT", "CPT"],
            "description": ["Hip", "Hip", "Hip"],
            "effective_price": [1000.0, 1100.0, 1200.0],
            "payer_name": ["P1", "P2", "P3"],
        }
    )
    out = procedure_confidence(scoped)
    assert out.iloc[0]["confidence"] == "LOW"


def test_ingest_with_audit_captures_parse_failures(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    good = raw_dir / "good.csv"
    bad = raw_dir / "bad.json"
    pd.DataFrame(
        {
            "hospital_name": ["PeaceHealth St. Joseph Medical Center"],
            "payer_name": ["Aetna"],
            "code": ["27447"],
            "code_type": ["CPT"],
            "description": ["Total knee arthroplasty"],
            "negotiated_rate": [10000.0],
        }
    ).to_csv(good, index=False)
    bad.write_text("{ this is not valid json", encoding="utf-8")

    prices, audit = ingest_with_audit(raw_dir)
    assert len(prices) == 1
    assert len(audit) == 2
    assert set(audit["status"].astype(str)) == {"parsed", "failed_parse"}
    failed = audit[audit["status"] == "failed_parse"].iloc[0]
    assert failed["error_type"] in {"JSONDecodeError", "ValueError"}
    assert isinstance(failed["sha256"], str) and len(failed["sha256"]) == 64


def test_run_writes_manifest_and_ingest_failures(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "processed"
    raw_dir.mkdir()
    out_dir.mkdir()

    pd.DataFrame(
        {
            "hospital_name": ["PeaceHealth St. Joseph Medical Center"],
            "payer_name": ["Aetna"],
            "code": ["27447"],
            "code_type": ["CPT"],
            "description": ["Total knee arthroplasty"],
            "negotiated_rate": [12000.0],
        }
    ).to_csv(raw_dir / "prices.csv", index=False)

    hospitals_csv = tmp_path / "hospitals.csv"
    procedures_csv = tmp_path / "procedures.csv"
    pd.DataFrame({"hospital_name": ["PeaceHealth St. Joseph Medical Center"]}).to_csv(hospitals_csv, index=False)
    pd.DataFrame({"code": ["27447"], "code_type": ["CPT"], "description": ["Total knee arthroplasty"]}).to_csv(
        procedures_csv, index=False
    )

    import argparse

    args = argparse.Namespace(
        input=raw_dir,
        hospitals=hospitals_csv,
        procedures=procedures_csv,
        focus_hospital="PeaceHealth St. Joseph Medical Center",
        output=out_dir,
    )
    run(args)

    manifest_path = out_dir / "run_manifest.json"
    failures_path = out_dir / "ingest_failures.csv"
    assert manifest_path.exists()
    assert failures_path.exists()

    import json

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["ingest"]["files_parsed"] == 1
    assert manifest["outputs"]["normalized_prices_rows"] == 1

    failures = pd.read_csv(failures_path)
    assert failures.empty
