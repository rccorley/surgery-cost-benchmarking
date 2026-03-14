# CLAUDE.md — Surgery Cost Benchmarking

## Project Overview

End-to-end hospital price transparency benchmarking tool for the **Bellingham → Seattle corridor**. Ingests CMS-mandated machine-readable files (MRFs) from hospitals, normalizes pricing into a canonical schema, and provides both an admin benchmarking dashboard and a patient-facing cost calculator.

**Primary focus hospital:** PeaceHealth St. Joseph Medical Center (Bellingham, WA)

**Baseline app goal:** Help someone from Bellingham see whether it's beneficial to travel to Seattle (or intermediate cities) for a given procedure based on real negotiated rate data.

## Build & Run

```bash
source .venv/bin/activate

# Run tests
python -m pytest tests/ -v

# Run benchmark pipeline
python src/benchmark.py \
  --input data/raw \
  --hospitals config/hospitals.csv \
  --procedures config/surgical_procedures.csv \
  --focus-hospital "PeaceHealth St. Joseph Medical Center" \
  --output data/processed

# Launch patient calculator (port 8502)
streamlit run src/patient_calculator.py --server.port 8502

# Launch admin dashboard
streamlit run src/dashboard.py
```

## Key Architecture Decisions

### Data Pipeline
- **`benchmark.py`** handles all MRF parsing and normalization
- PeaceHealth publishes a **wide-format CSV** (columns like `standard_charge|payer|plan|negotiated_dollar`)
- Providence/Swedish publish **CMS-schema JSON** files
- All data normalized to: `hospital_name, payer_name, code, code_type, description, negotiated_rate, cash_price, source_file`

### PeaceHealth `estimated_amount` Fallback
Many PeaceHealth payers use `negotiated_percentage` or `negotiated_algorithm` instead of `negotiated_dollar`. CMS requires hospitals to also publish an `estimated_amount` column with the calculated dollar value. The pipeline extracts these as a fallback, which increased PeaceHealth coverage from ~13 to ~29 payers.

### Episode Cost Estimation
Facility fees come from **actual hospital negotiated rate data**. Other episode components (surgeon, anesthesia, pathology, etc.) are **CMS benchmark estimates** using multipliers in `patient_estimator.py`. The UI makes this distinction clear with green/orange labels.

### Insurance Document OCR
Uses **EasyOCR** (free, offline, Python-only) for extracting plan benefits from SBC screenshots and billing/EOB statements. Regex parsing handles common patterns. No cloud API dependency.

## Current Coverage

- **78 procedures** (25 CPT codes + 53 DRG codes) in `config/surgical_procedures.csv`
- **~5,870 normalized price records** across 11 hospitals (deduplicated)
- **~147 raw payers → 34 canonical insurer groups** via `payer_normalizer.py`
- **13 hospitals configured** in the Bellingham → Seattle corridor (11 with data, 2 non-compliant — see table below)
- **100 tests** passing
- **New columns**: setting, gross_charge, charge_min, charge_max, is_outlier, payer_group, payer_canonical

### Corridor Hospital Status

| Hospital | City | Status | Format | Notes |
|----------|------|--------|--------|-------|
| PeaceHealth St. Joseph | Bellingham | ✅ Downloaded | Craneware ZIP/CSV | Focus hospital. Wide-format with `estimated_amount` fallback |
| PeaceHealth United General | Sedro-Woolley | ✅ Downloaded | Craneware ZIP/CSV | Same format as St. Joseph |
| Skagit Valley Hospital | Mount Vernon | ⚠️ Non-compliant | CSV | **MRF URLs return 404** — see Compliance Notes below |
| Cascade Valley Hospital | Arlington | ⚠️ Non-compliant | CSV | **MRF URLs return 404** — see Compliance Notes below |
| Providence Everett | Everett | ✅ Downloaded | CMS JSON | Providence system |
| Swedish Edmonds | Edmonds | ✅ Downloaded | CMS JSON | Providence/Swedish system |
| Swedish Medical Center | Seattle | ✅ Downloaded | CMS JSON | First Hill campus |
| Swedish Cherry Hill | Seattle | ✅ Downloaded | CMS JSON | Providence/Swedish system |
| Swedish Issaquah | Issaquah | ✅ Downloaded | CMS JSON | Providence/Swedish system |
| UW Medical Center | Seattle | ✅ Downloaded | CMS JSON | 98,954 items. Browser download required (Akamai 403 blocks CLI) |
| Harborview Medical Center | Seattle | ✅ Downloaded | CMS JSON | 95,950 items. UW Medicine system, browser download required |
| Overlake Medical Center | Bellevue | ✅ Downloaded | CMS JSON | 16,969 items. Via HospitalPriceDisclosure.com portal (browser required) |
| EvergreenHealth | Kirkland | ✅ Downloaded | CSV | 92.7 MB. Azure blob storage, direct download works |

**✅ Downloaded** = data in `data/raw/`, included in pipeline output
**⚠️ Non-compliant** = MRF URLs broken/missing — hospital not meeting CMS price transparency requirements
**🔧 Configured** = URL, config, parser mapping, and download command ready — just needs `download_mrf.py` or manual browser download

## File Reference

| File | Purpose |
|------|---------|
| `src/benchmark.py` | Core pipeline: parse MRFs → normalize → benchmark statistics |
| `src/patient_calculator.py` | Streamlit patient-facing cost calculator |
| `src/patient_estimator.py` | Episode cost estimation engine with CMS multipliers |
| `src/insurance_extractor.py` | EasyOCR + regex extraction from insurance document screenshots |
| `src/dashboard.py` | Admin-facing Streamlit benchmarking dashboard |
| `src/download_mrf.py` | Download hospital MRF files |
| `src/make_demo_data.py` | Generate small demo dataset for testing |
| `config/hospitals.csv` | Hospital names and regions |
| `config/hospital_sources.csv` | MRF download URLs and status |
| `config/surgical_procedures.csv` | Procedure codes to benchmark (CPT + DRG) |
| `tests/test_benchmark.py` | Pipeline and parser tests |
| `tests/test_patient_estimator.py` | Episode cost estimation tests |
| `tests/test_insurance_extractor.py` | OCR extraction regex tests |

---

## How to Extend to New Geographies

### Step 1: Discover Hospital MRF URLs

Every US hospital is required by CMS to publish a `cms-hpt.txt` file at their website root (similar to `robots.txt`). This file contains the URL to their machine-readable file.

**Discovery methods:**

1. **TPAFS Community Index** — The most comprehensive source of MRF URLs:
   - Repository: `https://github.com/TPAFS/transparency-data`
   - Contains pre-indexed MRF URLs for thousands of hospitals
   - Can filter by state, city, health system

2. **CMS Hospital Price Transparency index** — Official CMS repository:
   - Repository: `https://github.com/CMSgov/hospital-price-transparency`
   - Contains official schemas, validation tools, and the "70 shoppable services" list
   - Less useful for URL discovery than TPAFS

3. **Direct cms-hpt.txt lookup** — For a specific hospital:
   ```
   https://www.<hospital-domain>/cms-hpt.txt
   ```
   The file contains a JSON pointer to the MRF location.

4. **Google dorking** — Search for the standardized filename pattern:
   ```
   site:hospital-domain.org "standardcharges" filetype:json OR filetype:csv
   ```

### Step 2: Add the Hospital to Config

1. Add a row to `config/hospitals.csv`:
   ```csv
   hospital_name,city,state,region
   New Hospital Name,City,ST,corridor
   ```

2. Add download source to `config/hospital_sources.csv`:
   ```csv
   hospital_name,city,source_url,local_filename,download_status,notes
   New Hospital Name,City,https://...,new_hospital_standardcharges.json,,pending
   ```

3. Add to `src/download_mrf.py` `SOURCES` list:
   ```python
   ("new_hospital", "New Hospital Name", "https://...", "new_hospital_standardcharges.json"),
   ```

### Step 3: Add a Parser (if needed)

Most hospitals publish in one of two formats:

**Format A: CMS-schema JSON** (Providence, Swedish, UW Medicine)
- Already handled by `_load_json_cms()` in `benchmark.py`
- No additional parser needed — just add to config

**Format B: Wide-format CSV** (PeaceHealth, some Craneware-hosted hospitals)
- Columns like `standard_charge|payer|plan|negotiated_dollar`
- Currently handled by `flatten_peacehealth_wide()` in `benchmark.py`
- If a new hospital uses a similar wide format, you may need to generalize this function or add a new one
- Add a mapping in `_infer_hospital_name_from_source()` to assign the correct hospital name

**Format C: Flat CSV** (some smaller hospitals)
- Simple column mapping via `COLUMN_ALIASES` in `benchmark.py`
- Usually works out of the box if column names are standard

**Format D: Craneware API** (PeaceHealth, some others)
- URL pattern: `https://apim.services.craneware.com/api-pricing-transparency/api/public/{hospital_id}/charges/mrf`
- Returns a ZIP containing a wide-format CSV
- The `{hospital_id}` is a hash specific to each hospital

### Step 4: Download and Process

```bash
# Download new hospital's MRF
python src/download_mrf.py --only new_hospital

# Re-run the benchmark pipeline
python src/benchmark.py --input data/raw --hospitals config/hospitals.csv \
  --procedures config/surgical_procedures.csv \
  --focus-hospital "PeaceHealth St. Joseph Medical Center" \
  --output data/processed
```

### Step 5: Verify

```bash
# Check the new hospital appears in processed data
python -c "
import pandas as pd
df = pd.read_csv('data/processed/normalized_prices.csv')
print(df['hospital_name'].value_counts())
"
```

---

## Discovered MRF URLs (Not Yet Downloaded)

These URLs were discovered via TPAFS index and direct lookup but are blocked from automated download due to WAF/Cloudflare. Download manually in a browser and place in `data/raw/`.

### Bellingham / Skagit Region

| Hospital | URL | Format | Notes |
|----------|-----|--------|-------|
| Skagit Valley Hospital (Mount Vernon) | `https://www.skagitregionalhealth.org/docs/default-source/finance-and-billing/chargemasters/562392010_skagit-valley-hospital_standardcharges.csv` | CSV | Note: **CSV** version may bypass Cloudflare (original JSON URL was blocked) |
| Cascade Valley Hospital (Arlington) | `https://www.skagitregionalhealth.org/docs/default-source/finance-and-billing/chargemasters/562392010_cascade-valley-hospital_standardcharges.csv` | CSV | Same as above |
| PeaceHealth United General (Sedro-Woolley) | `https://apim.services.craneware.com/api/public/51492878d96ce15d3ad32eec16ccc830/charges/mrf` | Craneware ZIP | Same format as PeaceHealth St. Joseph |

### Seattle Metro / Eastside

| Hospital | URL | Format | Notes |
|----------|-----|--------|-------|
| UW Medical Center | `https://www.uwmedicine.org/sites/stevie/files/mrf/916001537_university-of-washington-medical-center_standardcharges.json` | JSON | CMS-schema JSON |
| Harborview Medical Center (Seattle) | `https://www.uwmedicine.org/sites/stevie/files/mrf/911631806_harborview-medical-center_standardcharges.json` | JSON | CMS-schema JSON, UW Medicine system |
| Overlake Medical Center (Bellevue) | `https://hospitalpricedisclosure.com/Download.aspx?pxi=jFpZaWS9NVsNmAQiukfKew*-*&f=iFd*_*cEPwhQHJy3lVvHy9uQ*-*` | Unknown | Behind HospitalPriceDisclosure portal |
| EvergreenHealth (Kirkland) | `https://stmlevergreenncus001.blob.core.windows.net/public/910844563_KING-COUNTY-PUBLIC-HOSPITAL-DISTRICT-NO2_standardcharges.csv` | CSV | Azure blob storage, may download directly |

---

## Future Architecture: Geographic Search

The long-term vision is allowing users to search for any geography and have the app dynamically discover, download, and process hospital data.

### Proposed Architecture

```
User enters zip code or city
        │
        ▼
┌─────────────────────────┐
│  Hospital Discovery     │  ← TPAFS index + CMS lookup
│  (by geography)         │    Filter by radius/region
└───────────┬─────────────┘
            │ list of hospitals + MRF URLs
            ▼
┌─────────────────────────┐
│  MRF Download Manager   │  ← Download with retry, WAF detection
│  (cache in data/raw/)   │    Alert user if manual download needed
└───────────┬─────────────┘
            │ raw files on disk
            ▼
┌─────────────────────────┐
│  Format Auto-Detection  │  ← Detect JSON vs CSV vs ZIP
│  + Parser Selection     │    Infer hospital name from filename
└───────────┬─────────────┘
            │ normalized records
            ▼
┌─────────────────────────┐
│  Benchmark Pipeline     │  ← Existing benchmark.py
│  (per-geography cache)  │
└───────────┬─────────────┘
            │ processed benchmark CSVs
            ▼
┌─────────────────────────┐
│  Streamlit App          │  ← Patient calculator + admin dashboard
│  (geography selector)   │    Compare across regions
└─────────────────────────┘
```

### Key Components to Build

1. **`src/hospital_discovery.py`** — Query TPAFS index by state/city/zip, return list of `(hospital_name, city, mrf_url, format_hint)`
2. **`src/mrf_downloader.py`** — Enhanced download manager with format detection, WAF retry, manual-download instructions, and caching
3. **`src/format_detector.py`** — Auto-detect MRF format (CMS JSON, wide CSV, flat CSV, Craneware ZIP) and select appropriate parser
4. **`config/regions.csv`** — Pre-configured regions (Bellingham corridor, Portland metro, Bay Area, etc.) with hospital lists
5. **Streamlit geography selector** — Add region/city dropdown to both apps, trigger download + pipeline on first use

### CMS Schema Versions

- **v2.0** (current, most hospitals): Five required rate types, payer-specific negotiated rates
- **v2.2** (transitional): Added estimated amounts for percentage/algorithm-based rates
- **v3.0** (effective April 2026): Adds median, 10th percentile, 90th percentile fields. Will require parser updates.

---

## Prioritized Task List

### Tier 1: Complete Bellingham Corridor (High Impact, Low Effort)

1. ~~**Configure corridor hospitals in pipeline**~~ ✅ DONE — All 13 corridor hospitals added to `hospitals.csv`, `hospital_sources.csv`, `download_mrf.py`, and `benchmark.py` parser mappings. 8 new hospital name inference tests added.

2. ~~**Download remaining hospital files**~~ ✅ DONE (11 of 13 hospitals) — Downloaded via CLI: PeaceHealth United General (Craneware API), EvergreenHealth (Azure blob). Downloaded via browser: UW Medical Center, Harborview, Overlake. **Skagit Valley and Cascade Valley are non-compliant** — their MRF URLs return 404 (see Compliance Notes).

### Tier 2: Improve Data Quality (Medium Impact, Medium Effort)

5. **Validate extracted rates against CMS "70 shoppable services"** — CMS publishes a list of 70 procedures that every hospital must price. Use this as a sanity check for data quality.

6. **Add de_identified min/max/median from gross charges** — PeaceHealth CSV includes `standard_charge|min`, `standard_charge|max`, `standard_charge|gross` columns. These provide useful bounds even when negotiated rates are missing.

7. **Improve episode cost multipliers** — Current CMS benchmark multipliers are rough estimates. Refine using CMS Physician Fee Schedule data for surgeon/anesthesia fees.

8. **Add confidence scoring to patient estimates** — Show users how confident the estimate is based on: (a) actual vs estimated data components, (b) number of payers with data, (c) rate variance.

### Tier 3: Expand Geography (High Impact, High Effort)

9. **Build hospital discovery module** — Query TPAFS index by state/city, return hospital list with MRF URLs. This is the foundation for geographic expansion.

10. **Build MRF format auto-detection** — Parse first few KB of a file to detect format (JSON schema vs wide CSV vs flat CSV vs ZIP). Select appropriate parser automatically.

11. **Add geography selector to Streamlit apps** — Dropdown for pre-configured regions or free-text city search. Trigger download + pipeline on first use.

12. **Pre-configure Portland, OR corridor** — Second geography to prove the extension pattern works. OHSU, Providence Portland, Legacy, Kaiser.

### Tier 4: Enhanced Features (Variable Impact)

13. **Add procedure search/autocomplete** — Currently 79 procedures in dropdown. Add a text search input that queries the full PeaceHealth procedure catalog (3,000+ CPTs, 800+ DRGs) for procedures not in the curated list.

14. **Historical price tracking** — CMS requires quarterly MRF updates. Store timestamped snapshots to show price trends.

15. **Payer network analysis** — Which payers appear across multiple hospitals? Identify narrow vs broad networks.

16. **Export / share results** — PDF or link-based sharing of cost estimates for discussing with providers.

17. **Mobile-responsive layout** — Current Streamlit layout works on desktop but could be improved for mobile users.

---

## Recent Learnings & Gotchas

### Data Quality (discovered issues & solutions)

#### Deduplication
- PeaceHealth wide-format CSV produces **duplicate rows** for the same hospital+code+payer. The wide-to-long melt can match the same payer across multiple column variants, creating up to 8x duplication per combo.
- **Solution:** Dedup on `(hospital_name, code, payer_name, effective_price, setting)` in `filter_scope()`. Rows with different prices are kept (they represent inpatient vs outpatient).
- This reduced records from ~6,633 to ~5,869 (removed 764 excess rows, 12% reduction).

#### Outlier Detection
- UW Medical Center has rates >$500K (e.g., $706K for DRG 267 / Cigna) — likely percentage-based rates applied to total charges rather than true negotiated dollars.
- Bottom rates ~$170 for shoulder arthroscopy at PeaceHealth — likely per-unit or component rates, not full procedure prices.
- **Solution:** Flag outliers using 3x IQR outside p10-p90 per procedure. Only 7 of 5,869 records flagged (0.1%) — conservative threshold.

#### EvergreenHealth Coverage Gap
- Only 4/77 procedures match (43239, 45378, 45385, 64721 — all outpatient scopes/carpal tunnel).
- **Root cause:** They genuinely don't publish 21 of our 25 surgical CPTs and have **zero inpatient negotiated rates** (0 out of 199K inpatient rows have `negotiated_dollar`). Zero DRG-level pricing.
- Their `code|2` column contains Revenue Codes (RC), not DRGs — values like 341, 460 are department billing codes, not MS-DRGs.
- **Not a parsing bug** — this is a data completeness issue on EvergreenHealth's end.

#### Payer Name Fragmentation
- Raw data has 147 unique payer name strings across hospitals.
- Same insurer appears as different strings: "Premera Blue Cross", "KLH Premera PPO", "Premera BCBS WA"
- **Solution:** `payer_normalizer.py` maps to 34 canonical insurer groups. Top 9 groups cover all 11 hospitals.
- Two-level normalization: `payer_group` (insurer only, e.g. "Aetna") and `payer_canonical` (insurer + plan type, e.g. "Aetna - Commercial") to avoid mixing Medicare and Commercial rates.

#### Cross-Hospital Plan Matching
- Exact payer_name matching for "Same Plan, Different Hospitals" only works when hospitals use identical payer strings — rare across different health systems.
- **Solution:** `compare_hospitals_by_group()` matches on `payer_canonical` (insurer + plan type) instead of exact payer name. This finds "Aetna - Commercial" across 3+ hospitals instead of one specific "Aetna Health - Commercial" string at 1 hospital.

#### New Pipeline Columns
- `setting` (inpatient/outpatient) — extracted from CMS v3.0 flat format and PeaceHealth wide format
- `gross_charge` — gross (list) charge from the hospital
- `charge_min`, `charge_max` — de-identified min/max rates
- `is_outlier` — boolean flag for statistical outliers
- `payer_group`, `payer_canonical` — normalized payer identifiers

### Data Parsing
- **PeaceHealth `estimated_amount` columns are critical** — Without them, you miss ~50% of payers. Always check for `estimated_amount|payer|plan` columns as fallback when `negotiated_dollar` is empty.
- **Dedup when merging `negotiated_dollar` + `estimated_amount`** — Some payers have both. Use a `seen_payer_codes` set to prefer `negotiated_dollar`.
- **Code type normalization matters** — Hospitals may use `MS-DRG`, `DRG`, or `APR-DRG`. Normalize all to `DRG`. Code values may be numeric or string — always compare as strings.
- **PeaceHealth has multiple code columns** (`code|1`, `code|2`, `code|3`) — Use `bfill` across them to get the first non-null.

### CMS Transparency Rules
- Hospitals must publish MRFs in **machine-readable format** (JSON or CSV) with specific required fields.
- The `cms-hpt.txt` file at the website root is the official discovery mechanism.
- Hospitals must include **gross charges, discounted cash price, payer-specific negotiated rates, and de-identified min/max** for each item.
- When rates are percentage-based or algorithm-based, hospitals must also publish the calculated `estimated_amount`.
- **v3.0 schema** (April 2026) adds percentile statistics — plan parser updates.

### Blocked Downloads
- **Cloudflare/WAF** blocks automated downloads from Skagit Regional, UW Medicine, and Overlake.
- **Try CSV URLs** instead of JSON — some hospitals host both and the CSV may not be behind the same WAF.
- **Craneware-hosted hospitals** (PeaceHealth) use a different API endpoint that is generally accessible.
- **HospitalPriceDisclosure.com** portal requires a browser session — cannot be automated easily.

### Streamlit
- `st.selectbox` supports native type-to-search — no custom autocomplete needed for the procedure dropdown.
- Use `st.session_state` to persist OCR-extracted insurance values across reruns.
- Table height auto-sizing: `height = min(header_px + row_px * len(df) + padding, max_height)`.
- EasyOCR first load downloads ~200MB model. Use lazy loading (`_reader = None` pattern) to avoid slowing app startup.

### numpy Compatibility
- **EasyOCR pulls numpy 2.x** which breaks pandas on Python 3.9. Pin `numpy<2` in requirements or virtualenv.

---

## CMS Compliance Notes

### National Compliance Landscape
- **November 2024** (PatientRightsAdvocate.org [7th Semi-Annual Report](https://www.patientrightsadvocate.org/seventh-semi-annual-hospital-price-transparency-report-november-2024)): Only **21.1% of US hospitals** were fully compliant with CMS price transparency rules, down from 34.5% in February 2024.
- **Early 2025** (PatientRightsAdvocate.org [Interim Report](https://www.patientrightsadvocate.org/interim-semi-annual-hospital-price-transparency-report)): Only **~15% of US hospitals** had sufficient dollar-and-cents pricing disclosure. 43% of hospitals were posting fewer actual prices than in November 2024.
- **Washington State SB 5493** (passed 2025) codifies federal transparency requirements into state law with a July 2027 deadline.
- CMS penalties: **$300/day** (≤30 beds), **$10/bed/day** (31-550 beds), **$5,500/day** (>550 beds).

### CMS v3.0 Schema (April 2026)
- Adds median, 10th percentile, 90th percentile, count fields
- Requires CEO attestation of accuracy
- Valid code types: CPT, HCPCS, NDC, DRG, MS-DRG, APR-DRG, APC, LOCAL, RC
- Valid methodologies: fee schedule, percent of total billed charges, per diem, case rate, other
- CMS has an official CLI validator: `npm install -g @cmsgov/hpt-validator-cli` → `cms-hpt-validator ./file.csv v3.0`
- Official schema repo: [github.com/CMSgov/hospital-price-transparency](https://github.com/CMSgov/hospital-price-transparency)
- Parser updates will be needed — see `flatten_standard_charge_information()` in `benchmark.py`

### Non-Compliant Hospitals in Corridor

#### Skagit Valley Hospital & Cascade Valley Hospital (Skagit Regional Health)
- **Status:** Non-compliant — MRF files are inaccessible (404 errors)
- **Discovery:** Their `cms-hpt.txt` files exist and point to correct-looking URLs:
  - `https://www.skagitregionalhealth.org/docs/default-source/finance-and-billing/chargemasters/562392010_skagit-valley-hospital_standardcharges.csv`
  - `https://www.skagitregionalhealth.org/docs/default-source/finance-and-billing/chargemasters/562392010_cascade-valley-hospital_standardcharges.csv`
- **Problem:** Both URLs return **404 Not Found** — tested both via CLI (curl) and browser. Adding `?sfvrsn=` versioned query parameters (from `cms-hpt.txt`) also 404s.
- **What they do publish:** Their price transparency page only shows "Charge Description Master" links (gross charges only), **not** the full MRF with payer-negotiated rates as required by CMS.
- **Impact:** These two hospitals cannot be included in the benchmarking tool until they publish compliant MRF files.
- **Action items:**
  1. Periodically re-check the URLs (Skagit Regional may fix them)
  2. Consider filing a complaint via CMS Hospital Price Transparency enforcement portal
  3. Check TPAFS index for updated URLs if Skagit Regional republishes

### TPAFS Index (Transparency-Data Repository)
- **Repository:** `https://github.com/TPAFS/transparency-data`
- **Key file:** `machine_readable_links.csv` — contains MRF URLs for thousands of hospitals
- **Limitation:** The file is very large and cannot be fully processed via web fetch. For comprehensive lookup, clone the repo and search locally:
  ```bash
  git clone https://github.com/TPAFS/transparency-data.git
  grep -i "washington\|skagit\|cascade\|overlake" transparency-data/machine_readable_links.csv
  ```
- **Hospital CCN lookup:** `existence_transparency/hospitals/hospitals.csv` maps hospital names to CMS Certification Numbers (CCN). Known CCNs for our corridor:
  - Harborview: 050370
  - UW Medical Center: 050371
  - Overlake: 050373

### Download Method Notes
- **UW Medicine (UW Medical Center + Harborview):** CLI downloads get 403 Forbidden from Akamai CDN. Must download via browser, then copy to `data/raw/`.
- **Overlake:** Uses HospitalPriceDisclosure.com portal which requires a browser session. Navigate to portal, click download link, copy to `data/raw/`.
- **EvergreenHealth:** Direct Azure blob download works via CLI (`curl` or `download_mrf.py`).
- **PeaceHealth system:** Craneware API endpoints work via CLI.

---

## Git Workflow

### Branch Rules

- **Never commit directly to `main`.** All changes go through feature branches and PRs.
- PRs require at least one approving review before merge.
- Keep `main` deployable at all times.

### Commit / Push / PR Approval

- **Always propose commits, commit messages, and PR descriptions before executing them.** Do not commit, push, or create PRs without explicit user approval.
- Present the proposed commit message and list of files to be staged for review.
- For PRs, present the title and body for approval before running `gh pr create`.

### Branch Naming

Use this format: `<type>/<short-description>`

| Type | Use for | Example |
|------|---------|---------|
| `feature/` | New functionality | `feature/cross-hospital-comparison` |
| `fix/` | Bug fixes | `fix/payer-name-matching` |
| `data/` | Pipeline or data quality changes | `data/dedup-peacehealth-records` |
| `docs/` | Documentation only | `docs/update-readme` |
| `refactor/` | Code restructuring (no behavior change) | `refactor/extract-tab-views` |

Rules:
- Lowercase, hyphens only (no underscores, no slashes in the description)
- Keep it short but descriptive (3-5 words max)
- No ticket numbers unless using an issue tracker

### Commit Messages

```
<imperative verb> <what changed>

<optional body: why this change was made, context>
```

- Use imperative mood: "Add", "Fix", "Update", "Remove" — not "Added" or "Adds"
- First line under 72 characters
- Body explains **why**, not what (the diff shows what)

Examples:
```
Add 3-tier cross-hospital comparison fallback

payer_canonical matching only covered 12% of combos. Added payer_group
fallback to reach 60% coverage with clear labeling when comparing
across plan types.
```

### PR Conventions

- Title: short, under 70 chars, imperative mood
- Body: use the repo's PR template (Summary, Changes, Test plan, Screenshots)
- Always include test plan with checkboxes
- Link related issues if applicable

### Workflow

```
git checkout main
git pull origin main
git checkout -b feature/my-change
# ... make changes ...
PYTHONPATH=src python -m pytest tests/ -v
git add <specific files>
git commit -m "..."
git push -u origin feature/my-change
gh pr create
```

## Development Best Practices

### Before Committing
- Run `PYTHONPATH=src python -m pytest tests/ -v` — all tests must pass
- Verify `git status` — only stage files you intend to commit
- Never commit `.env`, credentials, or raw data files

### Streamlit Gotchas
- After changing imported modules, **kill and restart** Streamlit — it caches old module bytecode
- `st.selectbox` has built-in type-to-search — don't add separate text input filters
- `st.segmented_control` state changes need a moment to rerender; don't assume instant UI update
- Use `PYTHONPATH=src` when running from project root

### Data Pipeline Gotchas
- PeaceHealth wide-format CSV creates duplicate rows from multi-column melt — always dedup
- Code columns may be int or string depending on how CSV was loaded — use `str(code)` for comparisons after `load_normalized_prices()` converts to string dtype
- Payer names vary wildly across hospitals — always match via `payer_canonical` or `payer_group`, not raw `payer_name`
- EvergreenHealth `code|2` values are Revenue Codes, not DRGs — this is a data limitation, not a parsing bug
- Some hospitals publish percentage-based rates (e.g. "79.34% of charges") — use `estimated_amount` fallback
- Rates > $200K are likely percentage-based rates applied to total charges, not real negotiated dollars

### Testing Conventions
- Test files mirror source files: `src/benchmark.py` → `tests/test_benchmark.py`
- Mock external dependencies (OCR, network) in tests
- Use defensive column checks: `[c for c in cols if c in df.columns]` when deduplicating
- Test with both string and numeric code values
