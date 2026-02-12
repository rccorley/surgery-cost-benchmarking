# AGENTS.md — Instructions for AI Coding Agents

This file provides instructions for AI agents (Claude Code, Copilot, Cursor, etc.) working on this codebase.

## Critical Rules

1. **Never commit directly to `main`.** Always create a feature branch and open a PR.
2. **Never force-push to `main`.** This is a destructive action that can lose work.
3. **Never commit secrets, credentials, or raw data files.** The `.gitignore` excludes `data/raw/` and `data/external/` for a reason.
4. **Run tests before committing.** `PYTHONPATH=src python -m pytest tests/ -v` must pass.
5. **Never amend a commit after a failed pre-commit hook.** Create a new commit instead.

## Git Workflow

### Creating a Branch

```bash
git checkout main
git pull origin main
git checkout -b <type>/<short-description>
```

Branch types: `feature/`, `fix/`, `data/`, `docs/`, `refactor/`

Branch names: lowercase, hyphen-separated, 3-5 words. Example: `feature/add-cost-breakdown`

### Committing

- Stage specific files — avoid `git add .` or `git add -A`
- Commit message: imperative mood, under 72 chars, explains **why**
- Use HEREDOC format for multi-line commit messages

### Opening a PR

```bash
git push -u origin <branch-name>
gh pr create --title "Short title" --body "$(cat <<'EOF'
## Summary
- Bullet points

## Test plan
- [ ] Tests pass
- [ ] App starts

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `src/` | Application source code |
| `tests/` | Pytest test files (mirror `src/` naming) |
| `config/` | CSV config files (hospitals, procedures) |
| `data/raw/` | Hospital MRF files (gitignored) |
| `data/processed/` | Pipeline output CSVs (gitignored except `.gitkeep`) |
| `scripts/` | Utility scripts |
| `reports/` | Generated analysis reports |

## Key Files

| File | What it does |
|------|-------------|
| `src/benchmark.py` | Core pipeline: download → parse → normalize → benchmark |
| `src/patient_calculator.py` | Streamlit app entry point |
| `src/patient_estimator.py` | Episode cost estimation engine + procedure labels |
| `src/payer_normalizer.py` | Maps raw payer names → canonical insurer groups |
| `src/tab_patient_view.py` | Patient cost calculator tab UI |
| `src/insurance_extractor.py` | OCR extraction from insurance documents |

## How to Run

```bash
# Tests
PYTHONPATH=src python -m pytest tests/ -v

# Pipeline
python src/benchmark.py --input data/raw --output data/processed

# App
streamlit run src/patient_calculator.py
```

## Code Patterns to Follow

### Imports
- Use relative imports within `src/` (e.g., `from patient_estimator import BenefitDesign`)
- Path references use `Path(__file__).resolve().parents[1]` — never hardcode absolute paths

### DataFrames
- After `load_normalized_prices()`, codes are string dtype — use `str(code)` for comparisons
- Column existence checks before operations: `[c for c in cols if c in df.columns]`
- Payer matching: use `payer_canonical` or `payer_group` columns, never raw `payer_name` for cross-hospital comparison

### Streamlit
- After modifying imported modules, kill and restart Streamlit — it caches old bytecode
- `st.selectbox` has built-in search — don't add separate `st.text_input` filters
- Use `render_wrapped_table()` from `ui_tables.py` for consistent table styling

### Tests
- Mirror source file naming: `src/foo.py` → `tests/test_foo.py`
- Mock external dependencies (OCR, network calls)
- Current count: 100 tests across 7 files — don't decrease this number

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| PeaceHealth CSV creates duplicate rows | Dedup on `(hospital_name, code, payer_name, effective_price, setting)` |
| EvergreenHealth code\|2 looks like DRGs | They're Revenue Codes — this is a data limitation, not a bug |
| Rates > $200K | Likely percentage-based, not real dollars — flag as outliers |
| Cross-hospital payer matching fails | Use tiered fallback: exact → payer_canonical → payer_group |
| Streamlit shows stale UI after code change | Kill process and restart, don't just refresh browser |
| `git add .` stages raw data | Stage specific files by name instead |
