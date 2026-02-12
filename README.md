# Surgery Cost Benchmarking — Hospital Price Transparency

End-to-end hospital price transparency benchmarking tool for the **Bellingham → Seattle corridor**. Ingests CMS-mandated machine-readable files (MRFs) from hospitals, normalizes pricing into a canonical schema, and provides both an admin benchmarking dashboard and a patient-facing cost calculator.

**Anyone can adapt this to their own geography** — see [Run This for Your Area](#run-this-for-your-area).

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
| Procedures | 78 (25 CPT + 53 DRG) |
| Normalized price records | ~5,870 (deduplicated) |
| Canonical payer groups | 34 (from ~147 raw payer names) |
| Tests | 100 |

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

> Skagit Valley and Cascade Valley (Skagit Regional Health) have broken MRF URLs (404) and only publish gross charges, not the full MRF with payer-negotiated rates.

## Quick Start

```bash
git clone https://github.com/rccorley/surgery-cost-benchmarking.git
cd surgery-cost-benchmarking

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Download hospital MRF data
python src/download_mrf.py

# Run the benchmark pipeline
python src/benchmark.py \
  --input data/raw \
  --hospitals config/hospitals.csv \
  --procedures config/surgical_procedures.csv \
  --focus-hospital "PeaceHealth St. Joseph Medical Center" \
  --output data/processed

# Launch the patient cost calculator
streamlit run src/patient_calculator.py

# Launch the admin benchmarking dashboard
streamlit run src/dashboard.py
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

## Project Structure

```
├── README.md
├── CLAUDE.md                      # Detailed dev guide, architecture, compliance notes
├── CONTRIBUTING.md                # How to contribute
├── LICENSE                        # MIT License
├── requirements.txt
├── config/
│   ├── hospitals.csv              # Hospital names and regions
│   ├── hospital_sources.csv       # MRF download URLs and status
│   └── surgical_procedures.csv    # 78 procedures to benchmark (CPT + DRG)
├── data/
│   ├── raw/                       # Hospital MRF files (not in git)
│   └── processed/                 # Pipeline output CSVs
├── src/
│   ├── benchmark.py               # Core pipeline: parse → normalize → benchmark
│   ├── patient_calculator.py      # Streamlit patient cost calculator
│   ├── patient_estimator.py       # Episode cost estimation with CMS multipliers
│   ├── payer_normalizer.py        # Maps raw payer names to canonical groups
│   ├── insurance_extractor.py     # EasyOCR + regex for insurance documents
│   ├── dashboard.py               # Streamlit admin dashboard
│   ├── download_mrf.py            # Hospital MRF downloader
│   ├── tab_patient_view.py        # Patient tab UI
│   ├── tab_hospital_view.py       # Hospital comparison tab UI
│   ├── tab_surgeon_view.py        # Surgeon market intel tab UI
│   └── make_demo_data.py          # Generate demo data for testing
├── scripts/                       # Utility scripts (MIPS download, audits)
├── reports/                       # Generated analysis reports and charts
└── tests/                         # 100 tests across 7 test files
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
PYTHONPATH=src python -m pytest tests/ -v
```

100 tests across 7 test files.

## Run This for Your Area

This tool is designed to work with **any US hospital market**. To adapt it:

1. Edit `config/hospitals.csv` and `config/hospital_sources.csv` with your local hospitals
2. Find each hospital's MRF URL (search "[Hospital Name] machine readable file" or check their website)
3. Download the MRF files: `python src/download_mrf.py`
4. Run the pipeline: `python src/benchmark.py --input data/raw --output data/processed`
5. Launch: `streamlit run src/patient_calculator.py`

See `CLAUDE.md` for detailed documentation on supported MRF formats and known data quality issues.

## Key Design Decisions

- **PeaceHealth `estimated_amount` fallback** — Many payers use percentage-based rates. The pipeline extracts CMS-required `estimated_amount` as a fallback, roughly doubling PeaceHealth payer coverage.
- **CMS v3.0 flat format support** — EvergreenHealth and other newer MRFs use a flat row-per-payer layout (vs PeaceHealth's wide column-per-payer format). Both are auto-detected.
- **Episode cost estimation** — Facility fees are actual negotiated rates; other components (surgeon, anesthesia, etc.) are CMS benchmark estimates. The UI clearly labels which is which.
- **Offline OCR** — EasyOCR runs locally with no cloud dependency. First load downloads a ~200MB model.
- **Payer normalization** — Two-level normalization maps ~147 raw payer strings to 34 canonical groups, enabling cross-hospital comparison even when hospitals name the same insurer differently.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

[MIT](LICENSE)

## Notes

- See `CLAUDE.md` for detailed architecture documentation, extension guide, CMS compliance notes, and data quality learnings.
- MRF data formats vary significantly across hospitals (CMS JSON, wide CSV, flat CSV, Craneware API). The pipeline auto-detects and normalizes all formats.
