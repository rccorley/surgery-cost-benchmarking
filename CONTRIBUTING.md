# Contributing

Thanks for your interest in contributing to the Surgery Cost Benchmarking project!

## Getting Started

1. Fork the repo and clone your fork
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run the tests to make sure everything works:
   ```bash
   PYTHONPATH=src python -m pytest tests/ -v
   ```

## Development Workflow

1. Create a feature branch from `main`
2. Make your changes
3. Run tests: `PYTHONPATH=src python -m pytest tests/ -v`
4. Commit with a clear message describing what and why
5. Push your branch and open a Pull Request

## Adding a New Geography

This project is designed to be extensible to any US hospital market. To add your area:

1. Add hospitals to `config/hospitals.csv` and `config/hospital_sources.csv`
2. Download their MRF files: `python src/download_mrf.py`
3. Run the pipeline: `python src/benchmark.py --input data/raw --output data/processed`
4. Launch the app: `streamlit run src/patient_calculator.py`

See `CLAUDE.md` for detailed documentation on hospital MRF formats, the parsing pipeline, and known data quality issues.

## Adding New Procedures

Add procedure codes (CPT or DRG) to `config/surgical_procedures.csv`, then re-run the pipeline.

## Code Style

- Python 3.9+
- Type hints on function signatures
- Docstrings on public functions
- Tests for new functionality

## Reporting Issues

Open a GitHub issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Which hospital/procedure/payer if relevant

## Data Quality

If you find bad data (wrong prices, missing hospitals, mismatched payer names), please open an issue. CMS transparency files vary wildly across hospitals, and community help identifying parsing issues is very valuable.
