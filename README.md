# Surgery Cost Benchmarking — Hospital Price Transparency

End-to-end hospital price transparency benchmarking tool for the **Bellingham → Seattle corridor**. Ingests CMS-mandated machine-readable files (MRFs) from hospitals, normalizes pricing into a canonical schema, and provides both an admin benchmarking dashboard and a patient-facing cost calculator.

## What It Does

- **Patient Cost Calculator** — Estimates total out-of-pocket surgery costs based on your insurance plan (deductible, coinsurance, out-of-pocket max). Compares prices across hospitals and payers.
- **Admin Benchmarking Dashboard** — Analyzes negotiated rate dispersion, hospital rankings, and payer contract outliers.
- **Insurance Document OCR** — Upload screenshots of your SBC or billing statement to auto-extract plan benefits.
- **Episode Cost Estimation** — Goes beyond facility fees to estimate full episode costs (surgeon, anesthesia, pathology, etc.) using CMS benchmark multipliers.

## Coverage

| Metric | Count |
|--------|-------|
| Hospitals with data | 11 |
| Hospitals configured | 13 |
| Procedures | 77 (25 CPT + 52 DRG) |
| Normalized price records | ~6,600 |
| Unique payers | ~147 |

### Corridor Hospitals

| Hospital | City | Status |
|----------|------|--------|
| PeaceHealth St. Joseph | Bellingham | ✅ Data |
| PeaceHealth United General | Sedro-Woolley | ✅ Data |
| Skagit Valley Hospital | Mount Vernon | ⚠️ Non-compliant |
| Cascade Valley Hospital | Arlington | ⚠️ Non-compliant |
| Providence Everett | Everett | ✅ Data |
| Swedish Edmonds | Edmonds | ✅ Data |
| Swedish Medical Center | Seattle | ✅ Data |
| Swedish Cherry Hill | Seattle | ✅ Data |
| Swedish Issaquah | Issaquah | ✅ Data |
| UW Medical Center | Seattle | ✅ Data |
| Harborview Medical Center | Seattle | ✅ Data |
| Overlake Medical Center | Bellevue | ✅ Data |
| EvergreenHealth | Kirkland | ✅ Data |

> Skagit Valley and Cascade Valley (Skagit Regional Health) have broken MRF URLs (404) and only publish gross charges, not the full MRF with payer-negotiated rates. See `CLAUDE.md` for compliance details.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the benchmark pipeline
python src/benchmark.py \
  --input data/raw \
  --hospitals config/hospitals.csv \
  --procedures config/surgical_procedures.csv \
  --focus-hospital "PeaceHealth St. Joseph Medical Center" \
  --output data/processed

# Launch the patient cost calculator
streamlit run src/patient_calculator.py --server.port 8502

# Launch the admin benchmarking dashboard
streamlit run src/dashboard.py

# Audit procedure coverage retention by hospital
python scripts/audit_procedure_coverage.py
```

### Downloading Hospital Data

Hospital MRF files are not checked into the repo (they're large). To download them:

```bash
# Download all hospitals (automated where possible)
python src/download_mrf.py

# Download a specific hospital
python src/download_mrf.py --only peacehealth_st_joseph

# Some hospitals block automated downloads (UW Medicine, Overlake).
# For those, download via browser and place files in data/raw/.
# See CLAUDE.md for details on each hospital's download method.
```

### Loading MIPS Outcomes Data (ZIP-friendly)

If you download the CMS Doctors & Clinicians public reporting ZIP manually,
you can extract required files automatically:

```bash
# Example: import PY2023 bundle and extract required CSVs
python scripts/import_mips_zip.py \
  --zip /path/to/your/cms_mips_bundle.zip \
  --year 2023

# Build the features used by patient/surgeon MIPS panels
python scripts/build_outcomes_features.py --year 2023
```

Required files extracted into `data/external/mips/2023/`:
- `ec_public_reporting.csv`
- `grp_public_reporting.csv`

## Project Structure

```

## Architecture

- Data model and integration design (MRF + MIPS + bridge + marts):
  - `reports/data_model_design.md`

```
├── README.md
├── CLAUDE.md                      # Detailed dev guide, architecture, compliance notes
├── requirements.txt
├── config/
│   ├── hospitals.csv              # Hospital names and regions
│   ├── hospital_sources.csv       # MRF download URLs and status
│   └── surgical_procedures.csv    # 77 procedures to benchmark (CPT + DRG)
├── data/
│   ├── raw/                       # Hospital MRF files (not in git)
│   └── processed/                 # Pipeline output CSVs
├── src/
│   ├── benchmark.py               # Core pipeline: parse → normalize → benchmark
│   ├── patient_calculator.py      # Streamlit patient cost calculator
│   ├── patient_estimator.py       # Episode cost estimation with CMS multipliers
│   ├── insurance_extractor.py     # EasyOCR + regex for insurance documents
│   ├── dashboard.py               # Streamlit admin dashboard
│   ├── download_mrf.py            # Hospital MRF downloader
│   └── make_demo_data.py          # Generate demo data for testing
└── tests/
    ├── test_benchmark.py          # 19 tests: pipeline, parsers, hospital inference
    ├── test_patient_estimator.py  # 25 tests: episode costs, waterfall, comparisons
    └── test_insurance_extractor.py # 25 tests: OCR regex, plan/billing extraction
```

## Pipeline Outputs

| File | Description |
|------|-------------|
| `normalized_prices.csv` | All parsed and normalized price records |
| `procedure_benchmark.csv` | Per-procedure statistics (median, IQR, p10/p90, CV) |
| `hospital_benchmark.csv` | Per-hospital aggregate statistics |
| `focus_hospital_rank.csv` | How the focus hospital ranks vs peers per procedure |
| `payer_dispersion.csv` | Price variation across payers within each hospital |
| `procedure_confidence.csv` | Data quality confidence scores (HIGH/MEDIUM/LOW) |

## Running Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

69 tests across 3 test files.

## Key Design Decisions

- **PeaceHealth `estimated_amount` fallback** — Many payers use percentage-based rates. The pipeline extracts CMS-required `estimated_amount` as a fallback, roughly doubling PeaceHealth payer coverage.
- **CMS v3.0 flat format support** — EvergreenHealth and other newer MRFs use a flat row-per-payer layout (vs PeaceHealth's wide column-per-payer format). Both are auto-detected.
- **Episode cost estimation** — Facility fees are actual negotiated rates; other components (surgeon, anesthesia, etc.) are CMS benchmark estimates. The UI clearly labels which is which.
- **Offline OCR** — EasyOCR runs locally with no cloud dependency. First load downloads a ~200MB model.

## Notes

- See `CLAUDE.md` for detailed architecture documentation, extension guide for new geographies, CMS compliance notes, and the prioritized task list.
- MRF data formats vary significantly across hospitals (CMS JSON, wide CSV, flat CSV, Craneware API). The pipeline auto-detects and normalizes all formats.
