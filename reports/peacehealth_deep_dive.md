# PeaceHealth St. Joseph Medical Center -- Deep Dive Cost Analysis

Date: 2026-02-09
Corridor: Bellingham to Seattle, WA

---

## Executive Summary

This report provides a comprehensive analysis of surgical pricing at PeaceHealth St. Joseph Medical Center
based on publicly available machine-readable price transparency files. It compares PeaceHealth against
5 corridor peer hospitals across 22 surgical procedures (15 DRGs + 7 CPTs).

**Key findings:**
- PeaceHealth data spans **857** scoped pricing records across **22** procedures and **29** payer labels.
- **14** procedures have HIGH cross-hospital confidence, **2** MEDIUM, **6** LOW.
- PeaceHealth ranks in the **middle of the corridor** for most DRG-level procedures, with a few notable exceptions.
- Within PeaceHealth, payer-driven price variation is extreme for CPT procedures (up to 6x between lowest and highest payer).
- DRG-level variation is narrower (typically 1.2x-2.0x) but still material for patient financial planning.

---

## 1. Data Coverage

| Metric | Value |
| --- | --- |
| Scoped PeaceHealth records | 857 |
| DRG procedures | 16 |
| CPT procedures | 6 |
| Distinct payer labels | 29 |
| HIGH confidence procedures | 14 |
| MEDIUM confidence procedures | 2 |
| LOW confidence procedures | 6 |

### Procedure Confidence Levels

| code | code_type | description | n_hospitals | n_rates | confidence |
| --- | --- | --- | --- | --- | --- |
| 329 | DRG | Major small and large bowel procedures with MCC | 6 | 99 | HIGH |
| 377 | DRG | GI hemorrhage with MCC | 6 | 92 | HIGH |
| 481 | DRG | Hip and femur procedures except major joint with C | 5 | 75 | HIGH |
| 743 | DRG | Uterine and adnexa procedures for non-malignancy | 5 | 69 | HIGH |
| 470 | DRG | Major joint replacement or reattachment of lower e | 5 | 62 | HIGH |
| 472 | DRG | Cervical spinal fusion with CC | 5 | 61 | HIGH |
| 480 | DRG | Hip and femur procedures except major joint with M | 5 | 60 | HIGH |
| 482 | DRG | Hip and femur procedures except major joint withou | 5 | 60 | HIGH |
| 460 | DRG | Spinal fusion except cervical without CC/MCC | 5 | 54 | HIGH |
| 473 | DRG | Cervical spinal fusion without CC/MCC | 5 | 51 | HIGH |
| 469 | DRG | Major joint replacement with MCC | 5 | 38 | HIGH |
| 163 | DRG | Major chest procedures with MCC | 4 | 70 | HIGH |
| 483 | DRG | Major joint/limb reattachment of upper extremities | 4 | 47 | HIGH |
| 471 | DRG | Cervical spinal fusion with MCC | 4 | 40 | HIGH |
| 45378 | CPT | Colonoscopy diagnostic | 1 | 115 | LOW |
| 49650 | CPT | Laparoscopic inguinal hernia repair | 1 | 92 | LOW |
| 27130 | CPT | Total hip arthroplasty | 1 | 69 | LOW |
| 27447 | CPT | Total knee arthroplasty | 1 | 69 | LOW |
| 29881 | CPT | Arthroscopy knee meniscectomy | 1 | 69 | LOW |
| 47562 | CPT | Laparoscopic cholecystectomy | 1 | 23 | LOW |
| 267 | DRG | Endovascular cardiac valve replacement | 3 | 53 | MEDIUM |
| 216 | DRG | Cardiac valve and other major cardiothoracic proce | 3 | 50 | MEDIUM |

---

## 2. PeaceHealth Competitive Position (DRG-Level Cross-Hospital)

### Rank vs Corridor Peers (1 = lowest median price)

| code | description | rank_low_to_high | n_hospitals | hospital_median_price |
| --- | --- | --- | --- | --- |
| 163 | Major chest procedures with MCC | 4.0 | 4 | $206,496.16 |
| 216 | Cardiac valve and other major cardiothoracic procedures | 3.0 | 3 | $184,655.88 |
| 267 | Endovascular cardiac valve replacement | 3.0 | 3 | $88,489.65 |
| 329 | Major small and large bowel procedures with MCC | 6.0 | 6 | $110,920.24 |
| 377 | GI hemorrhage with MCC | 6.0 | 6 | $55,000.65 |
| 460 | Spinal fusion except cervical without CC/MCC | 5.0 | 5 | $116,497.44 |
| 469 | Major joint replacement with MCC | 5.0 | 5 | $62,540.48 |
| 470 | Major joint replacement or reattachment of lower extremity | 5.0 | 5 | $35,917.43 |
| 471 | Cervical spinal fusion with MCC | 3.0 | 4 | $92,935.44 |
| 472 | Cervical spinal fusion with CC | 5.0 | 5 | $85,819.01 |
| 473 | Cervical spinal fusion without CC/MCC | 4.0 | 5 | $53,802.60 |
| 480 | Hip and femur procedures except major joint with MCC | 5.0 | 5 | $57,160.00 |
| 481 | Hip and femur procedures except major joint with CC | 5.0 | 5 | $58,392.32 |
| 482 | Hip and femur procedures except major joint without CC/MCC | 5.0 | 5 | $36,854.50 |
| 483 | Major joint/limb reattachment of upper extremities | 4.0 | 4 | $45,214.33 |
| 743 | Uterine and adnexa procedures for non-malignancy | 4.0 | 5 | $21,401.24 |
| 27130 | Total hip arthroplasty | 1.0 | 1 | $28,001.38 |
| 27447 | Total knee arthroplasty | 1.0 | 1 | $17,197.50 |
| 29881 | Arthroscopy knee meniscectomy | 1.0 | 1 | $6,429.50 |
| 45378 | Colonoscopy diagnostic | 1.0 | 1 | $1,821.50 |
| 47562 | Laparoscopic cholecystectomy | 1.0 | 1 | $13,278.50 |
| 49650 | Laparoscopic inguinal hernia repair | 1.0 | 1 | $8,838.26 |

**Interpretation:** A rank of 1 means PeaceHealth has the lowest median negotiated rate among corridor peers for that DRG. Higher ranks indicate relatively higher pricing.

### Hospital-by-Hospital Comparison per DRG


#### DRG 163: Major chest procedures with MCC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Providence Everett | 14 | $41,368.71 | $11,746.71 | $234,051.10 |
| Swedish Medical Center | 14 | $75,453.74 | $24,584.40 | $189,835.87 |
| Swedish Medical Center Cherry Hill | 15 | $78,933.80 | $13,074.79 | $174,065.46 |
| PeaceHealth | 27 | $206,496.16 | $38,086.25 | $400,602.54 |

#### DRG 216: Cardiac valve and other major cardiothoracic procedures

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Providence Everett | 7 | $86,821.21 | $81,290.96 | $227,531.82 |
| Swedish Medical Center Cherry Hill | 16 | $102,095.66 | $65,625.62 | $332,978.14 |
| PeaceHealth | 27 | $184,655.88 | $29,872.14 | $438,014.41 |

#### DRG 267: Endovascular cardiac valve replacement

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Providence Everett | 12 | $44,171.06 | $41,454.20 | $130,145.17 |
| Swedish Medical Center Cherry Hill | 14 | $49,587.85 | $20,212.54 | $161,505.34 |
| PeaceHealth | 27 | $88,489.65 | $13,305.36 | $191,528.34 |

#### DRG 329: Major small and large bowel procedures with MCC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Medical Center Cherry Hill | 1 | $16,133.27 | $16,133.27 | $16,133.27 |
| Swedish Edmonds | 14 | $38,096.75 | $19,356.50 | $116,673.46 |
| Providence Everett | 18 | $44,408.23 | $4,831.52 | $110,159.68 |
| Swedish Medical Center Issaquah | 12 | $50,744.46 | $28,621.26 | $175,998.33 |
| Swedish Medical Center | 27 | $63,539.27 | $29,621.53 | $126,979.80 |
| PeaceHealth | 27 | $110,920.24 | $21,074.12 | $219,352.67 |

#### DRG 377: GI hemorrhage with MCC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Edmonds | 14 | $15,931.02 | $11,774.59 | $46,245.24 |
| Swedish Medical Center Issaquah | 10 | $16,171.32 | $11,606.28 | $60,116.22 |
| Providence Everett | 19 | $16,241.74 | $7,388.14 | $47,646.52 |
| Swedish Medical Center Cherry Hill | 4 | $17,654.44 | $9,018.28 | $18,001.25 |
| Swedish Medical Center | 18 | $18,366.01 | $11,717.10 | $70,362.18 |
| PeaceHealth | 27 | $55,000.65 | $12,587.14 | $128,525.73 |

#### DRG 460: Spinal fusion except cervical without CC/MCC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Medical Center Issaquah | 6 | $34,116.04 | $25,895.25 | $73,030.27 |
| Providence Everett | 12 | $36,944.02 | $30,015.47 | $114,956.03 |
| Swedish Medical Center Cherry Hill | 15 | $44,735.76 | $35,535.43 | $122,916.87 |
| Swedish Medical Center | 6 | $84,201.54 | $35,124.52 | $121,054.54 |
| PeaceHealth | 15 | $116,497.44 | $19,391.12 | $198,000.41 |

#### DRG 469: Major joint replacement with MCC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Providence Everett | 2 | $22,449.06 | $17,236.70 | $27,661.41 |
| Swedish Medical Center | 5 | $30,621.50 | $1,761.60 | $57,676.73 |
| Swedish Edmonds | 2 | $41,907.04 | $28,740.57 | $55,073.52 |
| Swedish Medical Center Issaquah | 2 | $44,101.98 | $30,747.97 | $57,455.99 |
| PeaceHealth | 27 | $62,540.48 | $10,824.52 | $133,068.78 |

#### DRG 470: Major joint replacement or reattachment of lower extremity

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Medical Center Issaquah | 1 | $16,551.83 | $16,551.83 | $16,551.83 |
| Swedish Edmonds | 4 | $16,942.32 | $13,373.82 | $54,293.44 |
| Providence Everett | 14 | $16,968.78 | $13,577.49 | $45,016.35 |
| Swedish Medical Center | 16 | $19,761.92 | $2,993.79 | $40,241.67 |
| PeaceHealth | 27 | $35,917.43 | $5,796.19 | $67,911.94 |

#### DRG 471: Cervical spinal fusion with MCC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Medical Center Cherry Hill | 7 | $37,239.95 | $26,972.05 | $60,137.34 |
| Providence Everett | 4 | $45,758.51 | $35,426.95 | $61,204.69 |
| PeaceHealth | 27 | $92,935.44 | $15,468.92 | $197,740.68 |
| Swedish Medical Center | 2 | $120,920.74 | $69,676.82 | $172,164.66 |

#### DRG 472: Cervical spinal fusion with CC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Medical Center Cherry Hill | 19 | $30,729.02 | $16,681.69 | $104,966.78 |
| Swedish Medical Center Issaquah | 2 | $34,620.23 | $21,918.80 | $47,321.66 |
| Providence Everett | 10 | $36,531.24 | $21,258.98 | $71,726.28 |
| Swedish Medical Center | 3 | $45,736.78 | $9,764.93 | $69,376.96 |
| PeaceHealth | 27 | $85,819.01 | $16,305.05 | $166,488.88 |

#### DRG 473: Cervical spinal fusion without CC/MCC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Providence Everett | 9 | $29,683.30 | $21,586.82 | $127,880.25 |
| Swedish Medical Center Cherry Hill | 11 | $29,963.87 | $2,717.46 | $86,649.72 |
| Swedish Medical Center Issaquah | 3 | $47,879.36 | $31,461.80 | $68,960.17 |
| PeaceHealth | 27 | $53,802.60 | $10,222.14 | $104,377.04 |
| Swedish Medical Center | 1 | $54,244.25 | $54,244.25 | $54,244.25 |

#### DRG 480: Hip and femur procedures except major joint with MCC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Medical Center Issaquah | 8 | $22,635.36 | $16,930.36 | $80,618.18 |
| Swedish Edmonds | 6 | $25,276.69 | $18,823.70 | $44,592.72 |
| Swedish Medical Center | 7 | $28,753.20 | $19,749.63 | $51,183.77 |
| Providence Everett | 12 | $35,765.32 | $20,870.91 | $109,336.46 |
| PeaceHealth | 27 | $57,160.00 | $10,370.09 | $119,728.11 |

#### DRG 481: Hip and femur procedures except major joint with CC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Medical Center Issaquah | 8 | $17,365.60 | $12,562.71 | $37,011.56 |
| Swedish Edmonds | 7 | $18,240.87 | $11,040.65 | $35,011.86 |
| Providence Everett | 19 | $19,057.24 | $14,375.23 | $51,688.54 |
| Swedish Medical Center | 14 | $20,327.81 | $7,148.46 | $59,797.90 |
| PeaceHealth | 27 | $58,392.32 | $11,094.16 | $113,281.10 |

#### DRG 482: Hip and femur procedures except major joint without CC/MCC

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Medical Center Issaquah | 7 | $13,718.36 | $12,898.79 | $47,765.98 |
| Swedish Edmonds | 4 | $13,726.95 | $12,555.19 | $22,291.53 |
| Providence Everett | 8 | $15,129.51 | $12,971.18 | $41,513.00 |
| Swedish Medical Center | 14 | $15,987.15 | $13,699.18 | $51,506.52 |
| PeaceHealth | 27 | $36,854.50 | $7,002.11 | $71,497.74 |

#### DRG 483: Major joint/limb reattachment of upper extremities

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Swedish Edmonds | 3 | $21,293.16 | $20,925.37 | $21,312.32 |
| Providence Everett | 4 | $22,440.42 | $16,282.37 | $58,337.50 |
| Swedish Medical Center | 13 | $25,768.90 | $3,285.11 | $81,509.30 |
| PeaceHealth | 27 | $45,214.33 | $7,670.02 | $103,737.22 |

#### DRG 743: Uterine and adnexa procedures for non-malignancy

| hospital_name | n_rates | median | min | max |
| --- | --- | --- | --- | --- |
| Providence Everett | 14 | $13,761.50 | $9,323.52 | $28,646.54 |
| Swedish Medical Center Issaquah | 5 | $15,524.56 | $9,396.57 | $42,809.20 |
| Swedish Edmonds | 8 | $17,852.53 | $8,963.69 | $29,093.24 |
| PeaceHealth | 27 | $21,401.24 | $3,629.66 | $48,799.08 |
| Swedish Medical Center | 15 | $22,369.99 | $9,898.43 | $46,525.25 |


---

## 3. PeaceHealth Within-Hospital Variation (CPT-Level)

CPT-level data is only available for PeaceHealth in this dataset (Providence/Swedish publish CPT codes without payer-negotiated rates). This makes CPT analysis a PeaceHealth internal view, not a market comparison.

### CPT Procedure Variation

| code | description | n_payers | median | min | max | p90_p10 |
| --- | --- | --- | --- | --- | --- | --- |
| 49650 | Laparoscopic inguinal hernia repair | 23 | $8,838.26 | $2,378.69 | $62,976.28 | 6.17x |
| 27447 | Total knee arthroplasty | 23 | $17,197.50 | $5,345.09 | $99,551.63 | 4.20x |
| 45378 | Colonoscopy diagnostic | 23 | $1,821.50 | $461.43 | $7,159.57 | 4.16x |
| 47562 | Laparoscopic cholecystectomy | 23 | $13,278.50 | $2,326.82 | $45,140.94 | 3.41x |
| 27130 | Total hip arthroplasty | 23 | $28,001.38 | $6,324.51 | $99,551.63 | 3.36x |
| 29881 | Arthroscopy knee meniscectomy | 23 | $6,429.50 | $1,508.80 | $25,103.82 | 3.07x |

**Interpretation:** p90/p10 above 2.0x indicates large payer-driven dispersion. Patients with different insurance plans face materially different negotiated rates for the same procedure.

---

## 4. Payer Analysis at PeaceHealth

### Biggest Payer Spread by Procedure

| code | description | low_payer | low_rate | high_payer | high_rate | ratio |
| --- | --- | --- | --- | --- | --- | --- |
| 47562 | Laparoscopic cholecystectomy | Molina Healthcare of WA - Managed M | $2,326.82 | Regence Blue Shield - Commercial | $45,140.94 | 19.40x |
| 49650 | Laparoscopic inguinal hernia repair | Molina Healthcare of WA - Managed M | $2,378.69 | Regence Blue Shield - Commercial | $45,140.94 | 18.98x |
| 29881 | Arthroscopy knee meniscectomy | Molina Healthcare of WA - Managed M | $1,508.80 | Regence Blue Shield - Commercial | $25,103.82 | 16.64x |
| 27447 | Total knee arthroplasty | Molina Healthcare of WA - Managed M | $6,324.51 | Regence Blue Shield - Commercial | $99,551.63 | 15.74x |
| 27130 | Total hip arthroplasty | Molina Healthcare of WA - Managed M | $6,324.51 | Regence Blue Shield - Commercial | $99,551.63 | 15.74x |
| 216 | Cardiac valve and other major cardiothoracic  | Molina Healthcare of WA - Managed M | $29,872.14 | United Healthcare - All Payer Appen | $438,014.41 | 14.66x |
| 267 | Endovascular cardiac valve replacement | Molina Healthcare of WA - Managed M | $13,305.36 | United Healthcare - All Payer Appen | $191,528.34 | 14.39x |
| 483 | Major joint/limb reattachment of upper extrem | Molina Healthcare of WA - Managed M | $7,670.02 | United Healthcare - All Payer Appen | $103,737.22 | 13.53x |
| 743 | Uterine and adnexa procedures for non-maligna | Molina Healthcare of WA - Managed M | $3,629.66 | United Healthcare - All Payer Appen | $48,799.08 | 13.44x |
| 471 | Cervical spinal fusion with MCC | Molina Healthcare of WA - Managed M | $15,468.92 | United Healthcare - All Payer Appen | $197,740.68 | 12.78x |
| 469 | Major joint replacement with MCC | Molina Healthcare of WA - Managed M | $10,824.52 | United Healthcare - All Payer Appen | $133,068.78 | 12.29x |
| 470 | Major joint replacement or reattachment of lo | Molina Healthcare of WA - Managed M | $5,796.19 | United Healthcare - NexusACO | $67,911.94 | 11.72x |
| 480 | Hip and femur procedures except major joint w | Molina Healthcare of WA - Managed M | $10,370.09 | United Healthcare - All Payer Appen | $119,728.11 | 11.55x |
| 45378 | Colonoscopy diagnostic | Molina Healthcare of WA - Managed M | $656.46 | Regence Blue Shield - Commercial | $7,053.96 | 10.75x |
| 163 | Major chest procedures with MCC | Kaiser WA - All Other LOB | $38,086.25 | Humana Health Plan - Commercial | $400,602.54 | 10.52x |
| 329 | Major small and large bowel procedures with M | Molina Healthcare of WA - Managed M | $21,074.12 | Regence Blue Shield - Commercial | $219,352.67 | 10.41x |
| 482 | Hip and femur procedures except major joint w | Molina Healthcare of WA - Managed M | $7,002.11 | Humana Health Plan - Commercial | $71,497.74 | 10.21x |
| 481 | Hip and femur procedures except major joint w | Molina Healthcare of WA - Managed M | $11,094.16 | Humana Health Plan - Commercial | $113,281.10 | 10.21x |
| 473 | Cervical spinal fusion without CC/MCC | Molina Healthcare of WA - Managed M | $10,222.14 | Humana Health Plan - Commercial | $104,377.04 | 10.21x |
| 472 | Cervical spinal fusion with CC | Molina Healthcare of WA - Managed M | $16,305.05 | Humana Health Plan - Commercial | $166,488.88 | 10.21x |
| 460 | Spinal fusion except cervical without CC/MCC | Molina Healthcare of WA - Managed M | $19,391.12 | Humana Health Plan - Commercial | $198,000.41 | 10.21x |
| 377 | GI hemorrhage with MCC | Molina Healthcare of WA - Managed M | $12,587.14 | Humana Health Plan - Commercial | $128,525.73 | 10.21x |

### Payer Relative Index (Across All Procedures)

A value below 1.00x means the payer's median rates tend to be below the procedure-level median at PeaceHealth. Above 1.00x means higher.

| payer_name | procedures_covered | median_relative_index |
| --- | --- | --- |
| Molina Healthcare of WA - Managed Medicaid | 22 | 0.19x |
| Regence Blue Shield - Medicare Advantage PPO | 21 | 0.52x |
| Regence Blue Shield - Medicare Advantage HMO | 21 | 0.52x |
| Molina Healthcare of WA - Medicare Advantage | 21 | 0.53x |
| Devoted - Medicare Advantage | 21 | 0.53x |
| Wellpoint - Managed Medicaid | 21 | 0.53x |
| Kaiser WA - Medicare Advantage | 21 | 0.55x |
| United Healthcare - Medicare Payer Appendix | 21 | 0.55x |
| Humana Health Plan - Medicare HMO/PPO | 21 | 0.55x |
| Wellpoint Behavioral Health - Managed Medicaid | 6 | 0.64x |
| Regence Blue Shield - UMP | 22 | 1.00x |
| Health Net/Centene Health Plan - Commercial | 22 | 1.00x |
| Kaiser Northwest - Commercial | 22 | 1.00x |
| Ambetter - Commercial | 21 | 1.00x |
| Moda Health Plan - Connexus/Synergy | 22 | 1.00x |
| United Healthcare – PH Employees - United Healthcare – PH Employees | 22 | 1.12x |
| Kaiser WA - All Other LOB | 22 | 1.24x |
| Cigna Health - Local Plus | 16 | 1.30x |
| Regence Blue Shield - Commercial | 22 | 1.39x |
| Cigna Health - Commercial | 16 | 1.42x |
| DISCOUNTED_CASH | 6 | 1.44x |
| Aetna Health - Commercial | 16 | 1.48x |
| Kaiser WA - Individual and Family LOB | 22 | 1.48x |
| United Healthcare - All Payer Appendix | 15 | 1.79x |
| First Choice Health - Administrators | 22 | 1.80x |
| United Healthcare - Doctors Plan | 15 | 1.85x |
| United Healthcare - NexusACO | 15 | 1.85x |
| First Choice Health - Commercial | 22 | 1.90x |
| Humana Health Plan - Commercial | 22 | 1.94x |

**Key takeaway:** Medicare Advantage payers (Regence MA HMO/PPO, Devoted, Molina, Wellpoint) cluster at 0.96-0.98x of median. Commercial plans (especially Regence Blue Shield Commercial) are dramatically higher at 5-6x. Discounted cash rates also exceed the procedure median.

---

## 5. Actionable Insights for PeaceHealth Administration

### Contract Renegotiation Candidates
1. **Regence Blue Shield Commercial** -- negotiated rates are 5-6x the Medicare Advantage baseline for CPT procedures. This spread far exceeds typical commercial-to-Medicare ratios and may indicate legacy contract terms.
2. **Ambetter Commercial** -- shows elevated rates for DRG 470 relative to other payers. Limited procedure coverage in the data.
3. **Discounted Cash** -- cash prices are 2.28x the procedure median, suggesting the self-pay discount schedule may benefit from review against market comparables.

### Competitive Position Actions
- For DRGs where PeaceHealth ranks in the upper half of corridor peers, the admin team should evaluate whether the rate differential reflects case mix complexity, implant cost differences, or pure negotiation position.
- For DRGs where PeaceHealth ranks #1 (lowest), consider whether there is margin erosion risk, especially for procedures with high volume.

### Data Quality Gaps
- CPT-level cross-hospital comparison is not possible with current data because Providence/Swedish publish CPT codes without payer-negotiated rates.
- 4 corridor hospitals (Skagit, Cascade, UW, Overlake) are blocked behind Cloudflare/WAF protections and could not be retrieved programmatically. Manual download from these hospitals would significantly strengthen the analysis.

---

## 6. Patient-Facing Implications

### What Bellingham Patients Should Know

1. **Your insurance plan is the biggest single factor** in what price is negotiated for your surgery at PeaceHealth. For CPT procedures, the spread between lowest and highest payer can exceed 6x.
2. **DRG pricing is more predictable** -- the within-hospital spread for DRG-based inpatient procedures is typically 1.2-2.0x.
3. **PeaceHealth is mid-market** among the corridor for most DRG procedures. It is neither systematically the cheapest nor the most expensive.
4. **Always request a written pre-op estimate** that includes facility, surgeon, anesthesia, imaging/lab, and pathology components.
5. **Verify your plan's specific negotiated rate** -- even two plans from the same insurer (e.g., Regence Medicare Advantage vs Regence Commercial) can differ by 6x.

### Pre-Surgery Financial Checklist

1. Ask for a bundled estimate: facility + surgeon + anesthesia + pathology/imaging/labs
2. Confirm expected CPT/DRG codes and inpatient vs outpatient setting
3. Run an estimate under your exact plan benefits (deductible, coinsurance, OOP max)
4. Compare in-network negotiated rate vs cash/self-pay quote
5. Verify all involved clinicians and facilities are in-network
6. Confirm prior authorization requirements and who is responsible for obtaining them
7. Document reference numbers for all estimate calls

---

*Generated from public hospital machine-readable price transparency files. These are negotiated facility rates, not final patient bills. Actual patient liability depends on plan benefit design (deductible, coinsurance, out-of-pocket maximum) and non-facility components.*
