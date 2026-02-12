# Hackathon Project Proposal

## Title
Surgery Cost Benchmarking Using Public Price Transparency Data

## One-Liner
Turn fragmented hospital machine-readable price files into an analytically defensible benchmarking system for surgical negotiated rates.

## Why This Matters
Hospitals publish negotiated prices by payer, but the data are too inconsistent for real comparison. This project makes those public data usable for administrators and surgical leaders to evaluate competitiveness and variation.

## Primary Insight to Demonstrate
The same surgery can vary dramatically in negotiated facility price:
- across hospitals in the same market corridor
- across payers within a single hospital

## User Persona for Demo
**Primary:** Hospital admin/finance strategy leader
- Needs quick answers on whether rates are high, low, or volatile vs peers

**Secondary:** Surgical service line leader
- Needs procedure-level competitive context for growth and contracting strategy

## MVP Deliverable
Working pipeline:
1. Ingest machine-readable files.
2. Normalize procedure codes, payer names, and prices.
3. Compute benchmarking + dispersion metrics.
4. Visualize rank and variation in a small dashboard/notebook.

## Hackathon Scope
- Corridor focus: Bellingham to Seattle
- Small initial set of high-volume procedures
- 5–10 hospitals maximum for first pass

## Success Criteria
- At least one comparable benchmark table across corridor hospitals.
- Clear quantification of within-hospital payer dispersion.
- Focus hospital rank view for core procedures.

## Risks and Mitigations
- Heterogeneous file structures: start with generic schema mapping + iterative adapters.
- Missing/ambiguous code types: restrict to clean CPT/DRG subset first.
- Uneven payer naming: normalize into broad payer groups for MVP.
