"""Patient out-of-pocket cost estimator.

Takes a negotiated facility rate and a patient's benefit design parameters
(deductible remaining, coinsurance percentage, out-of-pocket maximum remaining)
and estimates the patient's likely financial responsibility.

Includes total episode cost estimation using CMS-benchmarked multipliers for
non-facility fee components (surgeon, anesthesia, pathology, imaging).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class BenefitDesign:
    """A patient's plan benefit parameters relevant to cost-sharing."""

    deductible_remaining: float
    coinsurance_pct: float  # e.g. 0.20 means patient pays 20%
    oop_max_remaining: float


@dataclass(frozen=True)
class PatientEstimate:
    """Estimated patient out-of-pocket breakdown for a single service."""

    negotiated_rate: float
    deductible_portion: float
    coinsurance_portion: float
    patient_total: float
    plan_pays: float
    hit_oop_max: bool


# ---------------------------------------------------------------------------
# Episode cost multipliers (CMS-benchmarked)
#
# Each entry maps a procedure code to the estimated percentage of the
# facility fee that each non-facility component adds.  For inpatient DRG
# payments the facility fee already bundles implants, room, nursing, and
# supplies — so the add-on is primarily surgeon + anesthesia.  For outpatient
# CPT procedures the facility fee is smaller and professional fees are a
# larger proportion.
#
# Sources: CMS Physician Fee Schedule 2024-2025, CMS Anesthesia Base Units,
# AAHKS cost breakdowns, JAMA Surgery operating-room cost analyses,
# published spinal-implant utilisation studies (see deep-dive report).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FeeComponents:
    """Non-facility fee components as a fraction of the facility fee."""

    surgeon: float          # surgeon professional fee
    anesthesia: float       # anesthesia fee
    pathology_lab: float    # pathology and lab
    imaging: float          # pre/post-op imaging
    category: str = ""      # human-readable category name

    @property
    def total_multiplier(self) -> float:
        """Multiplier to apply to facility fee to get total episode estimate."""
        return 1.0 + self.surgeon + self.anesthesia + self.pathology_lab + self.imaging


# -- Inpatient DRG procedures (facility fee bundles implants + room) -------

_JOINT_REPLACEMENT = FeeComponents(
    surgeon=0.105, anesthesia=0.08, pathology_lab=0.002, imaging=0.008,
    category="Joint Replacement (Inpatient DRG)",
)
_SPINAL_FUSION = FeeComponents(
    surgeon=0.12, anesthesia=0.10, pathology_lab=0.005, imaging=0.02,
    category="Spinal Fusion (Inpatient DRG)",
)
_MAJOR_INPATIENT = FeeComponents(
    surgeon=0.12, anesthesia=0.08, pathology_lab=0.01, imaging=0.02,
    category="Major Inpatient Surgery (DRG)",
)

# -- Outpatient CPT procedures (facility fee does NOT include professional) -

_GENERAL_SURGERY = FeeComponents(
    surgeon=0.40, anesthesia=0.15, pathology_lab=0.03, imaging=0.02,
    category="General Surgery (Outpatient)",
)
_GI_ENDOSCOPY = FeeComponents(
    surgeon=0.55, anesthesia=0.30, pathology_lab=0.10, imaging=0.0,
    category="GI Endoscopy (Outpatient)",
)
_ORTHOPEDIC_OUTPATIENT = FeeComponents(
    surgeon=0.35, anesthesia=0.12, pathology_lab=0.02, imaging=0.02,
    category="Orthopedic (Outpatient)",
)
_GYN_INPATIENT = FeeComponents(
    surgeon=0.15, anesthesia=0.08, pathology_lab=0.02, imaging=0.01,
    category="Gynecologic Surgery (Inpatient DRG)",
)
_CARDIAC_INPATIENT = FeeComponents(
    surgeon=0.15, anesthesia=0.10, pathology_lab=0.01, imaging=0.02,
    category="Cardiac Surgery (Inpatient DRG)",
)
_OB_DELIVERY = FeeComponents(
    surgeon=0.20, anesthesia=0.10, pathology_lab=0.01, imaging=0.005,
    category="Obstetric Delivery (Inpatient DRG)",
)
_BREAST_SURGERY = FeeComponents(
    surgeon=0.35, anesthesia=0.12, pathology_lab=0.08, imaging=0.03,
    category="Breast Surgery (Outpatient)",
)
_SPINE_OUTPATIENT = FeeComponents(
    surgeon=0.40, anesthesia=0.15, pathology_lab=0.01, imaging=0.03,
    category="Spine Surgery (Outpatient)",
)
_MINOR_OUTPATIENT = FeeComponents(
    surgeon=0.45, anesthesia=0.10, pathology_lab=0.02, imaging=0.01,
    category="Minor Outpatient Surgery",
)
_UROLOGY_INPATIENT = FeeComponents(
    surgeon=0.15, anesthesia=0.08, pathology_lab=0.03, imaging=0.02,
    category="Urologic Surgery (Inpatient DRG)",
)

EPISODE_COMPONENTS: dict[str, FeeComponents] = {
    # DRG - Joint Replacement
    "469": _JOINT_REPLACEMENT,
    "470": _JOINT_REPLACEMENT,
    # DRG - Joint Revision
    "466": _JOINT_REPLACEMENT,
    "467": _JOINT_REPLACEMENT,
    "468": _JOINT_REPLACEMENT,
    # DRG - Hip/Femur
    "480": _JOINT_REPLACEMENT,
    "481": _JOINT_REPLACEMENT,
    "482": _JOINT_REPLACEMENT,
    "483": _JOINT_REPLACEMENT,
    # DRG - Spinal Fusion (cervical)
    "471": _SPINAL_FUSION,
    "472": _SPINAL_FUSION,
    "473": _SPINAL_FUSION,
    # DRG - Spinal Fusion (non-cervical)
    "460": _SPINAL_FUSION,
    # DRG - Major chest / cardiac / bowel / GI
    "163": _MAJOR_INPATIENT,
    "216": _CARDIAC_INPATIENT,
    "267": _CARDIAC_INPATIENT,
    "231": _CARDIAC_INPATIENT,
    "232": _CARDIAC_INPATIENT,
    "233": _CARDIAC_INPATIENT,
    "246": _CARDIAC_INPATIENT,
    "247": _CARDIAC_INPATIENT,
    "248": _CARDIAC_INPATIENT,
    "329": _MAJOR_INPATIENT,
    "377": _MAJOR_INPATIENT,
    # DRG - Appendectomy
    "341": _MAJOR_INPATIENT,
    "342": _MAJOR_INPATIENT,
    "343": _MAJOR_INPATIENT,
    # DRG - Hernia
    "349": _MAJOR_INPATIENT,
    "350": _MAJOR_INPATIENT,
    # DRG - Cholecystectomy
    "411": _MAJOR_INPATIENT,
    "412": _MAJOR_INPATIENT,
    "416": _MAJOR_INPATIENT,
    "417": _MAJOR_INPATIENT,
    # DRG - Mastectomy
    "582": _MAJOR_INPATIENT,
    "583": _MAJOR_INPATIENT,
    # DRG - Urology
    "714": _UROLOGY_INPATIENT,
    # DRG - Gynecologic
    "734": _GYN_INPATIENT,
    "736": _GYN_INPATIENT,
    "740": _GYN_INPATIENT,
    "743": _GYN_INPATIENT,
    # DRG - Obstetric delivery (cesarean + vaginal)
    "768": _OB_DELIVERY,
    "783": _OB_DELIVERY,
    "784": _OB_DELIVERY,
    "785": _OB_DELIVERY,
    "786": _OB_DELIVERY,
    "787": _OB_DELIVERY,
    "788": _OB_DELIVERY,
    "796": _OB_DELIVERY,
    "797": _OB_DELIVERY,
    "798": _OB_DELIVERY,
    "805": _OB_DELIVERY,
    "806": _OB_DELIVERY,
    "807": _OB_DELIVERY,
    # CPT - Outpatient ortho
    "27130": _JOINT_REPLACEMENT,   # THA
    "27447": _JOINT_REPLACEMENT,   # TKA
    "23472": _JOINT_REPLACEMENT,   # Total shoulder
    "29881": _ORTHOPEDIC_OUTPATIENT,  # Knee meniscectomy
    "29826": _ORTHOPEDIC_OUTPATIENT,  # Shoulder arthroscopic
    "29827": _ORTHOPEDIC_OUTPATIENT,  # Rotator cuff
    # CPT - General surgery
    "47562": _GENERAL_SURGERY,  # Lap chole
    "49650": _GENERAL_SURGERY,  # Lap hernia
    "49505": _GENERAL_SURGERY,  # Open hernia
    "49507": _GENERAL_SURGERY,  # Incarcerated hernia
    "44970": _GENERAL_SURGERY,  # Lap appendectomy
    # CPT - GI
    "45378": _GI_ENDOSCOPY,  # Colonoscopy
    "45385": _GI_ENDOSCOPY,  # Colonoscopy with polyp removal
    "43239": _GI_ENDOSCOPY,  # EGD with biopsy
    # CPT - Breast
    "19301": _BREAST_SURGERY,  # Lumpectomy
    "19303": _BREAST_SURGERY,  # Mastectomy
    # CPT - Gyn
    "58571": _GYN_INPATIENT,  # Lap hysterectomy
    "58661": _GYN_INPATIENT,  # Lap oophorectomy
    # CPT - OB
    "59514": _OB_DELIVERY,  # C-section
    # CPT - Spine outpatient
    "63030": _SPINE_OUTPATIENT,  # Lumbar discectomy
    "63047": _SPINE_OUTPATIENT,  # Lumbar laminectomy
    # CPT - Urology
    "55866": _GENERAL_SURGERY,  # Lap prostatectomy
    # CPT - Minor
    "42826": _MINOR_OUTPATIENT,  # Tonsillectomy
    "64721": _MINOR_OUTPATIENT,  # Carpal tunnel
}

# Fallback for codes not explicitly mapped
_DEFAULT_COMPONENTS = FeeComponents(
    surgeon=0.20, anesthesia=0.10, pathology_lab=0.02, imaging=0.02,
    category="Estimated (Default)",
)


def get_episode_components(code: str) -> FeeComponents:
    """Return fee components for a procedure code, with a sensible default."""
    return EPISODE_COMPONENTS.get(str(code), _DEFAULT_COMPONENTS)


@dataclass(frozen=True)
class EpisodeEstimate:
    """Estimated total episode cost breakdown."""

    facility_fee: float
    surgeon_fee: float
    anesthesia_fee: float
    pathology_lab_fee: float
    imaging_fee: float
    total_episode: float
    category: str
    is_default: bool  # True if using fallback multipliers


def estimate_patient_cost(
    negotiated_rate: float,
    benefit: BenefitDesign,
) -> PatientEstimate:
    """Compute estimated patient responsibility using standard waterfall.

    Waterfall:
      1. Patient pays the lesser of (negotiated_rate, deductible_remaining)
         toward deductible.
      2. Patient pays coinsurance_pct of remaining balance after deductible.
      3. Total patient cost is capped at oop_max_remaining.
    """
    if negotiated_rate <= 0:
        return PatientEstimate(
            negotiated_rate=negotiated_rate,
            deductible_portion=0.0,
            coinsurance_portion=0.0,
            patient_total=0.0,
            plan_pays=0.0,
            hit_oop_max=False,
        )

    # Step 1: deductible
    deductible_portion = min(negotiated_rate, benefit.deductible_remaining)
    remaining_after_deductible = negotiated_rate - deductible_portion

    # Step 2: coinsurance on the remainder
    coinsurance_portion = remaining_after_deductible * benefit.coinsurance_pct

    # Step 3: cap at OOP max
    raw_total = deductible_portion + coinsurance_portion
    hit_oop_max = raw_total > benefit.oop_max_remaining
    patient_total = min(raw_total, benefit.oop_max_remaining)
    plan_pays = negotiated_rate - patient_total

    return PatientEstimate(
        negotiated_rate=round(negotiated_rate, 2),
        deductible_portion=round(min(deductible_portion, patient_total), 2),
        coinsurance_portion=round(
            patient_total - min(deductible_portion, patient_total), 2
        ),
        patient_total=round(patient_total, 2),
        plan_pays=round(plan_pays, 2),
        hit_oop_max=hit_oop_max,
    )


def estimate_episode_cost(facility_fee: float, code: str) -> EpisodeEstimate:
    """Estimate total surgical episode cost from a facility fee.

    Uses CMS-benchmarked multipliers to estimate the separately-billed
    components (surgeon, anesthesia, pathology, imaging) that patients
    will also owe on top of the facility fee.
    """
    if facility_fee <= 0:
        return EpisodeEstimate(
            facility_fee=0, surgeon_fee=0, anesthesia_fee=0,
            pathology_lab_fee=0, imaging_fee=0, total_episode=0,
            category="", is_default=False,
        )

    comp = get_episode_components(code)
    surgeon = round(facility_fee * comp.surgeon, 2)
    anesthesia = round(facility_fee * comp.anesthesia, 2)
    pathlab = round(facility_fee * comp.pathology_lab, 2)
    imaging = round(facility_fee * comp.imaging, 2)
    total = round(facility_fee + surgeon + anesthesia + pathlab + imaging, 2)

    return EpisodeEstimate(
        facility_fee=round(facility_fee, 2),
        surgeon_fee=surgeon,
        anesthesia_fee=anesthesia,
        pathology_lab_fee=pathlab,
        imaging_fee=imaging,
        total_episode=total,
        category=comp.category,
        is_default=(comp is _DEFAULT_COMPONENTS),
    )


# ---------------------------------------------------------------------------
# Helpers for working with the normalized price dataset
# ---------------------------------------------------------------------------

PROCEDURE_LABELS: dict[str, str] = {
    # CPT - Orthopedic
    "27130": "Total Hip Replacement",
    "27447": "Total Knee Replacement",
    "23472": "Total Shoulder Replacement",
    "29826": "Shoulder Arthroscopy (Bone/Ligament Repair)",
    "29827": "Rotator Cuff Repair (Arthroscopic)",
    "29881": "Knee Arthroscopy (Meniscus)",
    # CPT - GI
    "43239": "Upper Endoscopy (EGD) with Biopsy",
    "45378": "Colonoscopy (Diagnostic)",
    "45385": "Colonoscopy with Polyp Removal",
    # CPT - General surgery
    "44970": "Appendectomy (Laparoscopic)",
    "47562": "Gallbladder Removal (Laparoscopic)",
    "49505": "Inguinal Hernia Repair (Open)",
    "49507": "Incarcerated Hernia Repair (Open)",
    "49650": "Inguinal Hernia Repair (Laparoscopic)",
    # CPT - Breast
    "19301": "Lumpectomy (Partial Mastectomy)",
    "19303": "Mastectomy (Simple/Complete)",
    # CPT - Gyn / OB
    "58571": "Hysterectomy (Laparoscopic, with Tubes/Ovaries)",
    "58661": "Ovary/Tube Removal (Laparoscopic)",
    "59514": "Cesarean Delivery",
    # CPT - Spine
    "63030": "Lumbar Discectomy",
    "63047": "Lumbar Laminectomy",
    # CPT - Urology
    "55866": "Prostatectomy (Laparoscopic/Robotic)",
    # CPT - ENT / Minor
    "42826": "Tonsillectomy (Age 12+)",
    "64721": "Carpal Tunnel Release",
    # DRG - Cardiac
    "163": "Major Chest Procedures (with MCC)",
    "216": "Cardiac Valve / Major Heart Surgery",
    "231": "Coronary Bypass (CABG) with Stent, with MCC",
    "232": "Coronary Bypass (CABG) with Stent, without MCC",
    "233": "Coronary Bypass (CABG) with Cardiac Cath",
    "246": "Heart Stent (Drug-Eluting) with MCC",
    "247": "Heart Stent (Drug-Eluting) without MCC",
    "248": "Heart Stent (Non-Drug-Eluting)",
    "267": "Heart Valve Replacement (Catheter-Based)",
    # DRG - GI / Abdominal
    "329": "Major Bowel Surgery (with MCC)",
    "341": "Appendectomy (with MCC)",
    "342": "Appendectomy (with CC)",
    "343": "Appendectomy (no complications)",
    "349": "Anal/Stomal Procedures (no CC/MCC)",
    "350": "Inguinal/Femoral Hernia (with MCC)",
    "377": "GI Bleeding Treatment (with MCC)",
    "411": "Cholecystectomy with CDE (with MCC)",
    "412": "Cholecystectomy with CDE (with CC)",
    "416": "Cholecystectomy, Open (no complications)",
    "417": "Cholecystectomy, Laparoscopic (with MCC)",
    # DRG - Spine
    "460": "Spinal Fusion, Non-Cervical (no complications)",
    # DRG - Joint
    "466": "Hip/Knee Replacement Revision (with MCC)",
    "467": "Hip/Knee Replacement Revision (with CC)",
    "468": "Hip/Knee Replacement Revision (no complications)",
    "469": "Major Joint Replacement (with MCC)",
    "470": "Major Joint Replacement / Reattachment",
    "471": "Cervical Spinal Fusion (with MCC)",
    "472": "Cervical Spinal Fusion (with CC)",
    "473": "Cervical Spinal Fusion (no complications)",
    "480": "Hip/Femur Procedures (with MCC)",
    "481": "Hip/Femur Procedures (with CC)",
    "482": "Hip/Femur Procedures (no complications)",
    "483": "Upper Extremity Joint Reattachment",
    # DRG - Breast
    "582": "Mastectomy for Cancer (with CC/MCC)",
    "583": "Mastectomy for Cancer (no complications)",
    # DRG - Urology
    "714": "Prostatectomy, Transurethral (no complications)",
    # DRG - Gynecologic
    "734": "Radical Hysterectomy",
    "736": "Ovarian/Adnexal Cancer Surgery",
    "740": "Uterine/Adnexal Cancer Surgery (with CC)",
    "743": "Uterine / Ovarian Procedures (Non-Cancer)",
    # DRG - Obstetric
    "768": "Vaginal Delivery with OR Procedure",
    "783": "C-Section with Sterilization (with MCC)",
    "784": "C-Section with Sterilization (with CC)",
    "785": "C-Section with Sterilization (no complications)",
    "786": "C-Section (with MCC)",
    "787": "C-Section (with CC)",
    "788": "C-Section (no complications)",
    "796": "Vaginal Delivery with Sterilization/D&C (with MCC)",
    "797": "Vaginal Delivery with Sterilization/D&C (with CC)",
    "798": "Vaginal Delivery with Sterilization/D&C (no complications)",
    "805": "Vaginal Delivery (with MCC)",
    "806": "Vaginal Delivery (with CC)",
    "807": "Vaginal Delivery (no complications)",
}


def procedure_label(code: str, description: str | None = None) -> str:
    """Return a patient-friendly label for a procedure code."""
    label = PROCEDURE_LABELS.get(str(code))
    if label:
        return label
    if description and str(description) not in ("", "<NA>", "nan"):
        return str(description)
    return f"Procedure {code}"


def load_normalized_prices(processed_dir: Path) -> pd.DataFrame:
    """Load the normalized_prices.csv and add patient-friendly labels."""
    path = processed_dir / "normalized_prices.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if df.empty:
        return df
    df["hospital_name"] = df["hospital_name"].astype("string")
    df["payer_name"] = df["payer_name"].astype("string").fillna("UNKNOWN")
    df["code"] = df["code"].astype("string")
    df["code_type"] = df["code_type"].astype("string")
    df["description"] = df["description"].astype("string")
    df["effective_price"] = pd.to_numeric(df["effective_price"], errors="coerce")
    df = df[df["effective_price"].notna() & (df["effective_price"] > 0)]
    df["procedure_label"] = df.apply(
        lambda r: procedure_label(r["code"], r.get("description")), axis=1
    )
    return df


def lookup_negotiated_rate(
    df: pd.DataFrame,
    hospital: str,
    payer: str,
    code: str,
) -> pd.Series:
    """Return matching effective_price values for a hospital/payer/code combo."""
    mask = (
        (df["hospital_name"] == hospital)
        & (df["payer_name"] == payer)
        & (df["code"] == str(code))
    )
    return df.loc[mask, "effective_price"]


def estimate_for_procedure(
    df: pd.DataFrame,
    hospital: str,
    payer: str,
    code: str,
    benefit: BenefitDesign,
) -> list[PatientEstimate]:
    """Return patient estimates for every matching rate row."""
    rates = lookup_negotiated_rate(df, hospital, payer, code)
    return [estimate_patient_cost(r, benefit) for r in rates]


def compare_payers(
    df: pd.DataFrame,
    hospital: str,
    code: str,
    benefit: BenefitDesign,
) -> pd.DataFrame:
    """Compare estimated patient cost across all payers for a procedure."""
    subset = df[(df["hospital_name"] == hospital) & (df["code"] == str(code))]
    if subset.empty:
        return pd.DataFrame()

    rows = []
    for payer, group in subset.groupby("payer_name"):
        median_rate = group["effective_price"].median()
        est = estimate_patient_cost(median_rate, benefit)
        rows.append(
            {
                "payer": payer,
                "negotiated_rate": est.negotiated_rate,
                "your_estimated_cost": est.patient_total,
                "plan_pays": est.plan_pays,
                "deductible_portion": est.deductible_portion,
                "coinsurance_portion": est.coinsurance_portion,
                "hits_oop_max": est.hit_oop_max,
            }
        )
    return pd.DataFrame(rows).sort_values("your_estimated_cost")


def compare_hospitals(
    df: pd.DataFrame,
    payer: str,
    code: str,
    benefit: BenefitDesign,
) -> pd.DataFrame:
    """Compare estimated patient cost across all hospitals for a procedure."""
    subset = df[(df["payer_name"] == payer) & (df["code"] == str(code))]
    if subset.empty:
        return pd.DataFrame()

    rows = []
    for hospital, group in subset.groupby("hospital_name"):
        median_rate = group["effective_price"].median()
        est = estimate_patient_cost(median_rate, benefit)
        rows.append(
            {
                "hospital": hospital,
                "negotiated_rate": est.negotiated_rate,
                "your_estimated_cost": est.patient_total,
                "plan_pays": est.plan_pays,
                "deductible_portion": est.deductible_portion,
                "coinsurance_portion": est.coinsurance_portion,
                "hits_oop_max": est.hit_oop_max,
            }
        )
    return pd.DataFrame(rows).sort_values("your_estimated_cost")


def compare_hospitals_by_group(
    df: pd.DataFrame,
    payer: str,
    code: str,
    benefit: BenefitDesign,
) -> pd.DataFrame:
    """Compare across hospitals using payer_canonical (insurer + plan type).

    Matches on both the insurer group AND the plan type (Commercial, Medicare,
    Medicaid) so we don't mix Aetna Commercial with Aetna Medicare rates.
    Uses payer_canonical (e.g. "Aetna - Commercial") for apples-to-apples
    comparison across hospitals.
    """
    if "payer_canonical" not in df.columns:
        return pd.DataFrame()

    payer_rows = df[(df["payer_name"] == payer) & (df["code"] == str(code))]
    if payer_rows.empty or payer_rows["payer_canonical"].isna().all():
        return pd.DataFrame()

    canonical = payer_rows["payer_canonical"].iloc[0]
    if not canonical or canonical in ("Other", "Self-Pay / Cash"):
        return pd.DataFrame()

    subset = df[(df["payer_canonical"] == canonical) & (df["code"] == str(code))]
    if subset.empty:
        return pd.DataFrame()

    rows = []
    for hospital, hgroup in subset.groupby("hospital_name"):
        median_rate = hgroup["effective_price"].median()
        est = estimate_patient_cost(median_rate, benefit)
        plan_label = hgroup["payer_name"].value_counts().index[0]
        rows.append(
            {
                "hospital": hospital,
                "plan_at_hospital": plan_label,
                "negotiated_rate": est.negotiated_rate,
                "your_estimated_cost": est.patient_total,
                "plan_pays": est.plan_pays,
                "deductible_portion": est.deductible_portion,
                "coinsurance_portion": est.coinsurance_portion,
                "hits_oop_max": est.hit_oop_max,
            }
        )
    result = pd.DataFrame(rows).sort_values("your_estimated_cost")
    # Store canonical label for the UI
    result.attrs["canonical_label"] = canonical
    return result


def compare_hospitals_by_insurer(
    df: pd.DataFrame,
    payer: str,
    code: str,
    benefit: BenefitDesign,
) -> pd.DataFrame:
    """Compare across hospitals using payer_group (insurer only).

    This is the broadest fallback — matches all plans from the same insurer
    (e.g. all Aetna plans regardless of Commercial/Medicare/Medicaid).
    Used when payer_canonical matching yields ≤1 hospital.
    """
    if "payer_group" not in df.columns:
        return pd.DataFrame()

    payer_rows = df[(df["payer_name"] == payer) & (df["code"] == str(code))]
    if payer_rows.empty or payer_rows["payer_group"].isna().all():
        return pd.DataFrame()

    group = payer_rows["payer_group"].iloc[0]
    if not group or group in ("Other", "Self-Pay / Cash"):
        return pd.DataFrame()

    subset = df[(df["payer_group"] == group) & (df["code"] == str(code))]
    if subset.empty:
        return pd.DataFrame()

    rows = []
    for hospital, hgroup in subset.groupby("hospital_name"):
        median_rate = hgroup["effective_price"].median()
        est = estimate_patient_cost(median_rate, benefit)
        plan_label = hgroup["payer_name"].value_counts().index[0]
        rows.append(
            {
                "hospital": hospital,
                "plan_at_hospital": plan_label,
                "negotiated_rate": est.negotiated_rate,
                "your_estimated_cost": est.patient_total,
                "plan_pays": est.plan_pays,
                "deductible_portion": est.deductible_portion,
                "coinsurance_portion": est.coinsurance_portion,
                "hits_oop_max": est.hit_oop_max,
            }
        )
    result = pd.DataFrame(rows).sort_values("your_estimated_cost")
    result.attrs["insurer_label"] = group
    return result
