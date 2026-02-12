# Cross-Hospital Surgical Cost Comparison Report

Date: 2026-02-09
Corridor: Bellingham to Seattle, WA

---

## Executive Summary

This report compares surgical procedure pricing across **6** hospitals in the Bellingham-to-Seattle
corridor using publicly available machine-readable price transparency files. The analysis covers
**22** surgical procedures with **1,418** total pricing records.

**Key findings:**
- **14** procedures have HIGH cross-hospital confidence (4+ hospitals, 30+ rates, 12+ payers).
- **2** procedures have MEDIUM confidence (2+ hospitals with meaningful payer coverage).
- Cross-hospital price variation ranges from 1.5x to 4.5x for the same DRG depending on hospital and payer.
- The same payer can negotiate dramatically different rates at different hospitals in the same corridor.
- Providence/Swedish system hospitals (5 of 6 in dataset) share similar payer panels but not identical rates.

---

## 1. Hospital Overview

### Participating Hospitals

| hospital_name | n_rates | median_price | p90 | cv |
| --- | --- | --- | --- | --- |
| Swedish Edmonds | 62 | $21,302.74 | $49,596.88 | 0.68 |
| PeaceHealth | 857 | $26,815.28 | $115,184.68 | 1.28 |
| Swedish Issaquah | 64 | $27,317.74 | $71,809.24 | 0.79 |
| Swedish Seattle | 155 | $30,943.29 | $88,085.43 | 0.81 |
| Providence Everett | 178 | $31,387.10 | $88,823.43 | 0.85 |
| Swedish Cherry Hill | 102 | $49,250.44 | $144,449.38 | 0.84 |

**Notes:**
- CV (coefficient of variation) measures overall price dispersion. Higher CV indicates more variation across all procedures and payers.
- 4 additional corridor hospitals (Skagit Valley, Cascade Valley, UW Medical Center, Overlake) could not be retrieved due to WAF/Cloudflare protections.

---

## 2. Cross-Hospital Comparable Procedures

### HIGH and MEDIUM Confidence Procedures

| code | code_type | description | n_hospitals | n_rates | n_unique_payers | p90_p10_ratio | confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 329 | DRG | Major small and large bowel procedures with MCC | 6 | 99 | 61 | 4.78x | HIGH |
| 377 | DRG | GI hemorrhage with MCC | 6 | 92 | 55 | 5.60x | HIGH |
| 481 | DRG | Hip and femur procedures except major joint with C | 5 | 75 | 55 | 4.52x | HIGH |
| 743 | DRG | Uterine and adnexa procedures for non-malignancy | 5 | 69 | 50 | 3.52x | HIGH |
| 470 | DRG | Major joint replacement or reattachment of lower e | 5 | 62 | 51 | 3.49x | HIGH |
| 472 | DRG | Cervical spinal fusion with CC | 5 | 61 | 50 | 5.38x | HIGH |
| 480 | DRG | Hip and femur procedures except major joint with M | 5 | 60 | 45 | 4.99x | HIGH |
| 482 | DRG | Hip and femur procedures except major joint withou | 5 | 60 | 47 | 4.27x | HIGH |
| 460 | DRG | Spinal fusion except cervical without CC/MCC | 5 | 54 | 40 | 4.34x | HIGH |
| 473 | DRG | Cervical spinal fusion without CC/MCC | 5 | 51 | 45 | 3.97x | HIGH |
| 469 | DRG | Major joint replacement with MCC | 5 | 38 | 34 | 3.83x | HIGH |
| 163 | DRG | Major chest procedures with MCC | 4 | 70 | 51 | 8.50x | HIGH |
| 483 | DRG | Major joint/limb reattachment of upper extremities | 4 | 47 | 42 | 3.83x | HIGH |
| 471 | DRG | Cervical spinal fusion with MCC | 4 | 40 | 38 | 4.32x | HIGH |
| 267 | DRG | Endovascular cardiac valve replacement | 3 | 53 | 48 | 3.35x | MEDIUM |
| 216 | DRG | Cardiac valve and other major cardiothoracic proce | 3 | 50 | 46 | 3.61x | MEDIUM |

**Confidence criteria:**
- HIGH: 4+ hospitals, 30+ rates, 12+ unique payers
- MEDIUM: 2+ hospitals, 12+ rates, 5+ unique payers
- LOW: insufficient cross-hospital or payer coverage

---

## 3. DRG Median Price Matrix (All Hospitals)

Each cell shows the median negotiated effective price for that DRG at that hospital.

| code | PeaceHealth | Providence Everett | Swedish Cherry Hill | Swedish Edmonds | Swedish Issaquah | Swedish Seattle |
| --- | --- | --- | --- | --- | --- | --- |
| 163 | $206,496.16 | $41,368.71 | $78,933.80 | - | - | $75,453.74 |
| 216 | $184,655.88 | $86,821.21 | $102,095.66 | - | - | - |
| 267 | $88,489.65 | $44,171.06 | $49,587.85 | - | - | - |
| 329 | $110,920.24 | $44,408.23 | $16,133.27 | $38,096.75 | $50,744.46 | $63,539.27 |
| 377 | $55,000.65 | $16,241.74 | $17,654.44 | $15,931.02 | $16,171.32 | $18,366.01 |
| 460 | $116,497.44 | $36,944.02 | $44,735.76 | - | $34,116.04 | $84,201.54 |
| 469 | $62,540.48 | $22,449.06 | - | $41,907.04 | $44,101.98 | $30,621.50 |
| 470 | $35,917.43 | $16,968.78 | - | $16,942.32 | $16,551.83 | $19,761.92 |
| 471 | $92,935.44 | $45,758.51 | $37,239.95 | - | - | $120,920.74 |
| 472 | $85,819.01 | $36,531.24 | $30,729.02 | - | $34,620.23 | $45,736.78 |
| 473 | $53,802.60 | $29,683.30 | $29,963.87 | - | $47,879.36 | $54,244.25 |
| 480 | $57,160.00 | $35,765.32 | - | $25,276.69 | $22,635.36 | $28,753.20 |
| 481 | $58,392.32 | $19,057.24 | - | $18,240.87 | $17,365.60 | $20,327.81 |
| 482 | $36,854.50 | $15,129.51 | - | $13,726.95 | $13,718.36 | $15,987.15 |
| 483 | $45,214.33 | $22,440.42 | - | $21,293.16 | - | $25,768.90 |
| 743 | $21,401.24 | $13,761.50 | - | $17,852.53 | $15,524.56 | $22,369.99 |

---

## 4. Detailed DRG-Level Comparisons


### DRG 163: Major chest procedures with MCC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Providence Everett | 14 | $41,368.71 | $11,746.71 | $234,051.10 | 0.82 |
| Swedish Seattle | 14 | $75,453.74 | $24,584.40 | $189,835.87 | 0.61 |
| Swedish Cherry Hill | 15 | $78,933.80 | $13,074.79 | $174,065.46 | 0.59 |
| PeaceHealth | 27 | $206,496.16 | $38,086.25 | $400,602.54 | 0.68 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Kaiser - Medicare Managed Care Plan | Providence Everett | $25,525.44 | Swedish Seattle | $43,833.96 | 1.72x |
| Molina - Medicaid Managed Care Plan | Providence Everett | $11,746.71 | Swedish Seattle | $27,112.20 | 2.31x |
| UnitedHealthCare - All Commercial Plans | Providence Everett | $113,224.96 | Swedish Seattle | $189,835.87 | 1.68x |
| UnitedHealthCare - Medicaid Managed Care | Providence Everett | $15,394.20 | Swedish Cherry Hill | $174,065.46 | 11.31x |
| UnitedHealthCare - Medicare Managed Care | Providence Everett | $40,564.32 | Swedish Cherry Hill | $46,509.26 | 1.15x |


### DRG 216: Cardiac valve and other major cardiothoracic procedures [MEDIUM]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Providence Everett | 7 | $86,821.21 | $81,290.96 | $227,531.82 | 0.48 |
| Swedish Cherry Hill | 16 | $102,095.66 | $65,625.62 | $332,978.14 | 0.56 |
| PeaceHealth | 27 | $184,655.88 | $29,872.14 | $438,014.41 | 0.52 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Blue Cross - Premera All Commercial Plan | Swedish Cherry Hill | $220,079.26 | Providence Everett | $227,531.82 | 1.03x |
| Community Health Plan of Washington - Me | Providence Everett | $86,773.50 | Swedish Cherry Hill | $91,867.98 | 1.06x |
| UnitedHealthCare - Medicaid Managed Care | Swedish Cherry Hill | $78,871.74 | Providence Everett | $81,290.96 | 1.03x |
| UnitedHealthCare - Medicare Managed Care | Providence Everett | $87,724.18 | Swedish Cherry Hill | $95,140.36 | 1.08x |


### DRG 267: Endovascular cardiac valve replacement [MEDIUM]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Providence Everett | 12 | $44,171.06 | $41,454.20 | $130,145.17 | 0.50 |
| Swedish Cherry Hill | 14 | $49,587.85 | $20,212.54 | $161,505.34 | 0.62 |
| PeaceHealth | 27 | $88,489.65 | $13,305.36 | $191,528.34 | 0.49 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Blue Cross - Premera Medicare Managed Ca | Providence Everett | $42,642.82 | Swedish Cherry Hill | $46,836.06 | 1.10x |
| Blue Shield - Regence All Commercial Pla | Providence Everett | $130,145.17 | Swedish Cherry Hill | $160,768.96 | 1.24x |
| Kaiser - Medicare Managed Care Plan | Providence Everett | $41,454.20 | Swedish Cherry Hill | $47,909.40 | 1.16x |
| Molina - Medicare Managed Care Plan | Providence Everett | $43,138.81 | Swedish Cherry Hill | $49,428.42 | 1.15x |
| UnitedHealthCare - Medicare Managed Care | Providence Everett | $42,819.48 | Swedish Cherry Hill | $48,202.71 | 1.13x |


### DRG 329: Major small and large bowel procedures with MCC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Cherry Hill | 1 | $16,133.27 | $16,133.27 | $16,133.27 | 0.00 |
| Swedish Edmonds | 14 | $38,096.75 | $19,356.50 | $116,673.46 | 0.53 |
| Providence Everett | 18 | $44,408.23 | $4,831.52 | $110,159.68 | 0.55 |
| Swedish Issaquah | 12 | $50,744.46 | $28,621.26 | $175,998.33 | 0.59 |
| Swedish Seattle | 27 | $63,539.27 | $29,621.53 | $126,979.80 | 0.37 |
| PeaceHealth | 27 | $110,920.24 | $21,074.12 | $219,352.67 | 0.54 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Aetna - All Commercial Plans | Swedish Issaquah | $39,566.00 | Swedish Seattle | $120,862.27 | 3.05x |
| UnitedHealthCare - All Commercial Plans | Providence Everett | $110,159.68 | Swedish Issaquah | $175,998.33 | 1.60x |
| UnitedHealthCare - Medicaid Managed Care | Swedish Edmonds | $22,072.20 | Swedish Seattle | $57,560.44 | 2.61x |
| Coordinated Care - Medicaid Managed Care | Swedish Cherry Hill | $16,133.27 | Swedish Seattle | $48,355.10 | 3.00x |
| Blue Cross - Premera All Commercial Plan | Swedish Issaquah | $77,803.06 | Providence Everett | $106,957.82 | 1.37x |


### DRG 377: GI hemorrhage with MCC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Edmonds | 14 | $15,931.02 | $11,774.59 | $46,245.24 | 0.51 |
| Swedish Issaquah | 10 | $16,171.32 | $11,606.28 | $60,116.22 | 0.63 |
| Providence Everett | 19 | $16,241.74 | $7,388.14 | $47,646.52 | 0.60 |
| Swedish Cherry Hill | 4 | $17,654.44 | $9,018.28 | $18,001.25 | 0.24 |
| Swedish Seattle | 18 | $18,366.01 | $11,717.10 | $70,362.18 | 0.60 |
| PeaceHealth | 27 | $55,000.65 | $12,587.14 | $128,525.73 | 0.65 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Kaiser - Medicare Managed Care Plan | Swedish Issaquah | $12,927.04 | Swedish Cherry Hill | $18,001.25 | 1.39x |
| UnitedHealthCare - Medicaid Managed Care | Swedish Cherry Hill | $9,018.28 | Swedish Issaquah | $26,014.23 | 2.88x |
| UnitedHealthCare - Medicare Managed Care | Swedish Edmonds | $13,804.88 | Swedish Seattle | $18,040.23 | 1.31x |
| Aetna - All Commercial Plans | Swedish Edmonds | $29,967.65 | Swedish Issaquah | $60,116.22 | 2.01x |
| Kaiser - All Commercial Plans | Swedish Issaquah | $16,243.28 | Swedish Edmonds | $21,751.17 | 1.34x |


### DRG 460: Spinal fusion except cervical without CC/MCC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Issaquah | 6 | $34,116.04 | $25,895.25 | $73,030.27 | 0.39 |
| Providence Everett | 12 | $36,944.02 | $30,015.47 | $114,956.03 | 0.51 |
| Swedish Cherry Hill | 15 | $44,735.76 | $35,535.43 | $122,916.87 | 0.52 |
| Swedish Seattle | 6 | $84,201.54 | $35,124.52 | $121,054.54 | 0.35 |
| PeaceHealth | 15 | $116,497.44 | $19,391.12 | $198,000.41 | 0.37 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Blue Cross - Premera All Commercial Plan | Swedish Cherry Hill | $83,834.49 | Providence Everett | $87,958.70 | 1.05x |
| UnitedHealthCare - Medicare Managed Care | Swedish Issaquah | $30,403.86 | Swedish Cherry Hill | $35,535.43 | 1.17x |
| Aetna - All Commercial Plans | Swedish Seattle | $121,054.54 | Swedish Cherry Hill | $121,054.54 | 1.00x |
| Aetna - Medicare Managed Care - HMO | Swedish Cherry Hill | $35,657.18 | Swedish Issaquah | $36,467.70 | 1.02x |
| Aetna - Medicare Managed Care - PPO | Swedish Seattle | $35,124.52 | Swedish Cherry Hill | $35,964.26 | 1.02x |


### DRG 469: Major joint replacement with MCC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Providence Everett | 2 | $22,449.06 | $17,236.70 | $27,661.41 | 0.23 |
| Swedish Seattle | 5 | $30,621.50 | $1,761.60 | $57,676.73 | 0.59 |
| Swedish Edmonds | 2 | $41,907.04 | $28,740.57 | $55,073.52 | 0.31 |
| Swedish Issaquah | 2 | $44,101.98 | $30,747.97 | $57,455.99 | 0.30 |
| PeaceHealth | 27 | $62,540.48 | $10,824.52 | $133,068.78 | 0.49 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| UnitedHealthCare - Medicare Managed Care | Providence Everett | $27,661.41 | Swedish Issaquah | $30,747.97 | 1.11x |
| Blue Cross - Premera Lifewise Exchange | Swedish Issaquah | $57,455.99 | Swedish Seattle | $57,676.73 | 1.00x |


### DRG 470: Major joint replacement or reattachment of lower extremity [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Issaquah | 1 | $16,551.83 | $16,551.83 | $16,551.83 | 0.00 |
| Swedish Edmonds | 4 | $16,942.32 | $13,373.82 | $54,293.44 | 0.66 |
| Providence Everett | 14 | $16,968.78 | $13,577.49 | $45,016.35 | 0.49 |
| Swedish Seattle | 16 | $19,761.92 | $2,993.79 | $40,241.67 | 0.45 |
| PeaceHealth | 27 | $35,917.43 | $5,796.19 | $67,911.94 | 0.46 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| UnitedHealthCare - Medicare Managed Care | Swedish Issaquah | $16,551.83 | Swedish Seattle | $17,485.86 | 1.06x |
| Aetna - All Commercial Plans | Swedish Seattle | $24,076.00 | Providence Everett | $45,016.35 | 1.87x |
| Blue Cross - Premera Medicare Managed Ca | Providence Everett | $16,746.40 | Swedish Seattle | $19,336.28 | 1.15x |
| Coordinated Care - Medicaid Managed Care | Swedish Edmonds | $13,373.82 | Swedish Seattle | $15,027.72 | 1.12x |
| Humana - Choice Care Medicare Managed Ca | Swedish Edmonds | $17,268.23 | Swedish Seattle | $17,930.08 | 1.04x |


### DRG 471: Cervical spinal fusion with MCC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Cherry Hill | 7 | $37,239.95 | $26,972.05 | $60,137.34 | 0.25 |
| Providence Everett | 4 | $45,758.51 | $35,426.95 | $61,204.69 | 0.20 |
| PeaceHealth | 27 | $92,935.44 | $15,468.92 | $197,740.68 | 0.49 |
| Swedish Seattle | 2 | $120,920.74 | $69,676.82 | $172,164.66 | 0.42 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Amerigroup - Medicaid Managed Care Plan | Swedish Cherry Hill | $33,498.55 | Providence Everett | $46,414.08 | 1.39x |
| UnitedHealthCare - Medicare Managed Care | Providence Everett | $35,426.95 | Swedish Cherry Hill | $48,304.88 | 1.36x |


### DRG 472: Cervical spinal fusion with CC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Cherry Hill | 19 | $30,729.02 | $16,681.69 | $104,966.78 | 0.59 |
| Swedish Issaquah | 2 | $34,620.23 | $21,918.80 | $47,321.66 | 0.37 |
| Providence Everett | 10 | $36,531.24 | $21,258.98 | $71,726.28 | 0.44 |
| Swedish Seattle | 3 | $45,736.78 | $9,764.93 | $69,376.96 | 0.59 |
| PeaceHealth | 27 | $85,819.01 | $16,305.05 | $166,488.88 | 0.56 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Blue Cross - Premera All Commercial Plan | Swedish Cherry Hill | $69,176.96 | Providence Everett | $71,726.28 | 1.04x |
| Blue Shield - Regence All Commercial Pla | Swedish Issaquah | $47,321.66 | Swedish Cherry Hill | $104,966.78 | 2.22x |
| Blue Cross - Premera Medicare Managed Ca | Swedish Cherry Hill | $16,681.69 | Providence Everett | $26,964.37 | 1.62x |
| Blue Shield - Uniform Exchange | Providence Everett | $62,497.92 | Swedish Cherry Hill | $64,638.41 | 1.03x |
| Coordinated Care - Ambetter Exchange | Swedish Cherry Hill | $52,387.02 | Providence Everett | $52,459.35 | 1.00x |


### DRG 473: Cervical spinal fusion without CC/MCC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Providence Everett | 9 | $29,683.30 | $21,586.82 | $127,880.25 | 0.67 |
| Swedish Cherry Hill | 11 | $29,963.87 | $2,717.46 | $86,649.72 | 0.68 |
| Swedish Issaquah | 3 | $47,879.36 | $31,461.80 | $68,960.17 | 0.31 |
| PeaceHealth | 27 | $53,802.60 | $10,222.14 | $104,377.04 | 0.51 |
| Swedish Seattle | 1 | $54,244.25 | $54,244.25 | $54,244.25 | 0.00 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Blue Shield - Regence All Commercial Pla | Swedish Issaquah | $47,879.36 | Swedish Cherry Hill | $86,649.72 | 1.81x |
| Blue Cross - Premera All Commercial Plan | Swedish Cherry Hill | $53,368.96 | Providence Everett | $59,948.64 | 1.12x |
| Molina - Medicaid Managed Care Plan | Swedish Cherry Hill | $18,334.48 | Providence Everett | $29,003.61 | 1.58x |
| UnitedHealthCare - All Commercial Plans | Providence Everett | $68,348.06 | Swedish Issaquah | $68,960.17 | 1.01x |
| UnitedHealthCare - Medicare Managed Care | Providence Everett | $21,904.00 | Swedish Cherry Hill | $23,253.06 | 1.06x |


### DRG 480: Hip and femur procedures except major joint with MCC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Issaquah | 8 | $22,635.36 | $16,930.36 | $80,618.18 | 0.67 |
| Swedish Edmonds | 6 | $25,276.69 | $18,823.70 | $44,592.72 | 0.30 |
| Swedish Seattle | 7 | $28,753.20 | $19,749.63 | $51,183.77 | 0.30 |
| Providence Everett | 12 | $35,765.32 | $20,870.91 | $109,336.46 | 0.57 |
| PeaceHealth | 27 | $57,160.00 | $10,370.09 | $119,728.11 | 0.49 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Kaiser - Medicare Managed Care Plan | Providence Everett | $25,360.34 | Swedish Seattle | $26,163.41 | 1.03x |
| UnitedHealthCare - Medicare Managed Care | Providence Everett | $25,243.01 | Swedish Seattle | $27,297.19 | 1.08x |
| Aetna - Medicare Managed Care - PPO | Swedish Issaquah | $17,275.77 | Swedish Seattle | $28,753.20 | 1.66x |
| Blue Cross - Premera Medicare Managed Ca | Swedish Issaquah | $19,823.17 | Providence Everett | $25,607.37 | 1.29x |
| Humana - Choice Care Medicare Managed Ca | Swedish Edmonds | $25,250.81 | Swedish Issaquah | $80,618.18 | 3.19x |


### DRG 481: Hip and femur procedures except major joint with CC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Issaquah | 8 | $17,365.60 | $12,562.71 | $37,011.56 | 0.42 |
| Swedish Edmonds | 7 | $18,240.87 | $11,040.65 | $35,011.86 | 0.35 |
| Providence Everett | 19 | $19,057.24 | $14,375.23 | $51,688.54 | 0.47 |
| Swedish Seattle | 14 | $20,327.81 | $7,148.46 | $59,797.90 | 0.60 |
| PeaceHealth | 27 | $58,392.32 | $11,094.16 | $113,281.10 | 0.55 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Blue Cross - Premera Medicare Managed Ca | Swedish Issaquah | $16,694.51 | Swedish Seattle | $22,509.16 | 1.35x |
| Kaiser - Medicare Managed Care Plan | Providence Everett | $17,448.53 | Swedish Seattle | $19,067.87 | 1.09x |
| UnitedHealthCare - Medicare Managed Care | Swedish Issaquah | $16,493.93 | Swedish Seattle | $19,200.58 | 1.16x |
| Blue Cross - Premera All Commercial Plan | Swedish Issaquah | $37,011.56 | Providence Everett | $49,337.21 | 1.33x |
| Humana - Choice Care Medicare Managed Ca | Swedish Issaquah | $16,572.99 | Swedish Seattle | $21,668.71 | 1.31x |


### DRG 482: Hip and femur procedures except major joint without CC/MCC [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Issaquah | 7 | $13,718.36 | $12,898.79 | $47,765.98 | 0.60 |
| Swedish Edmonds | 4 | $13,726.95 | $12,555.19 | $22,291.53 | 0.25 |
| Providence Everett | 8 | $15,129.51 | $12,971.18 | $41,513.00 | 0.50 |
| Swedish Seattle | 14 | $15,987.15 | $13,699.18 | $51,506.52 | 0.50 |
| PeaceHealth | 27 | $36,854.50 | $7,002.11 | $71,497.74 | 0.51 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| UnitedHealthCare - Medicare Managed Care | Swedish Edmonds | $13,649.89 | Swedish Seattle | $14,766.68 | 1.08x |
| Blue Shield - Regence All Commercial Pla | Swedish Edmonds | $22,291.53 | Providence Everett | $41,513.00 | 1.86x |
| Kaiser - Medicare Managed Care Plan | Swedish Issaquah | $12,898.79 | Swedish Seattle | $14,151.51 | 1.10x |
| Molina - Medicaid Managed Care Plan | Swedish Edmonds | $12,555.19 | Swedish Seattle | $13,699.18 | 1.09x |
| Aetna - Medicare Managed Care - HMO | Swedish Issaquah | $13,718.36 | Swedish Seattle | $15,856.26 | 1.16x |


### DRG 483: Major joint/limb reattachment of upper extremities [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Swedish Edmonds | 3 | $21,293.16 | $20,925.37 | $21,312.32 | 0.01 |
| Providence Everett | 4 | $22,440.42 | $16,282.37 | $58,337.50 | 0.56 |
| Swedish Seattle | 13 | $25,768.90 | $3,285.11 | $81,509.30 | 0.58 |
| PeaceHealth | 27 | $45,214.33 | $7,670.02 | $103,737.22 | 0.49 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| UnitedHealthCare - Medicare Managed Care | Swedish Edmonds | $20,925.37 | Swedish Seattle | $23,118.66 | 1.10x |
| Aetna - Medicare Managed Care - PPO | Swedish Edmonds | $21,293.16 | Swedish Seattle | $24,591.32 | 1.15x |
| Humana - Choice Care Medicare Managed Ca | Swedish Edmonds | $21,312.32 | Swedish Seattle | $25,768.90 | 1.21x |
| UnitedHealthCare - Medicaid Managed Care | Providence Everett | $16,282.37 | Swedish Seattle | $19,044.68 | 1.17x |


### DRG 743: Uterine and adnexa procedures for non-malignancy [HIGH]

**Hospital comparison:**

| hospital_name | n_rates | median | min | max | cv |
| --- | --- | --- | --- | --- | --- |
| Providence Everett | 14 | $13,761.50 | $9,323.52 | $28,646.54 | 0.42 |
| Swedish Issaquah | 5 | $15,524.56 | $9,396.57 | $42,809.20 | 0.58 |
| Swedish Edmonds | 8 | $17,852.53 | $8,963.69 | $29,093.24 | 0.41 |
| PeaceHealth | 27 | $21,401.24 | $3,629.66 | $48,799.08 | 0.49 |
| Swedish Seattle | 15 | $22,369.99 | $9,898.43 | $46,525.25 | 0.49 |

**Same-payer cross-hospital spread (top shared payers):**

| payer | lowest_hospital | lowest_rate | highest_hospital | highest_rate | ratio |
| --- | --- | --- | --- | --- | --- |
| Blue Cross - Premera All Commercial Plan | Swedish Edmonds | $18,894.84 | Swedish Issaquah | $42,809.20 | 2.27x |
| Coordinated Care - Cascade Care Select E | Providence Everett | $14,345.82 | Swedish Seattle | $20,215.56 | 1.41x |
| Aetna - All Commercial Plans | Swedish Issaquah | $12,846.00 | Swedish Seattle | $46,525.25 | 3.62x |
| Blue Shield - Regence All Commercial Pla | Swedish Edmonds | $20,717.28 | Providence Everett | $26,883.82 | 1.30x |
| Molina - Medicaid Managed Care Plan | Providence Everett | $9,323.52 | Swedish Seattle | $9,898.43 | 1.06x |



---

## 5. Payer Market Presence

Payers appearing at 2+ hospitals (sorted by hospital coverage):

| payer_name | n_hospitals | n_procedures | n_rates | median_rate |
| --- | --- | --- | --- | --- |
| Aetna - All Commercial Plans | 5 | 11 | 21 | $46,525.25 |
| Blue Cross - Premera All Commercial Plans | 5 | 15 | 32 | $68,728.07 |
| Coordinated Care - Medicaid Managed Care Plan | 5 | 11 | 19 | $19,356.50 |
| Molina - Medicaid Managed Care Plan | 5 | 14 | 30 | $16,809.32 |
| UnitedHealthCare - All Commercial Plans | 5 | 12 | 23 | $82,980.52 |
| Blue Cross - Premera Medicare Managed Care Plan | 5 | 11 | 22 | $23,194.76 |
| UnitedHealthCare - Medicaid Managed Care Plan | 5 | 11 | 24 | $20,481.74 |
| Kaiser - All Commercial Plans | 5 | 13 | 23 | $29,963.87 |
| UnitedHealthCare - Medicare Managed Care Plan | 5 | 16 | 50 | $25,272.78 |
| Kaiser - Medicare Managed Care Plan | 5 | 16 | 35 | $25,360.34 |
| Humana - Choice Care Medicare Managed Care Plan | 4 | 14 | 26 | $27,136.98 |
| Community Health Plan of Washington - Medicare Managed Care Plan | 4 | 4 | 5 | $51,688.54 |
| Cigna - All Commercial Plans | 4 | 8 | 13 | $93,883.03 |
| Amerigroup - Medicaid Managed Care Plan | 4 | 11 | 16 | $22,564.53 |
| Molina - Medicare Managed Care Plan | 4 | 5 | 9 | $43,138.81 |
| Aetna - Medicare Managed Care - PPO | 4 | 14 | 24 | $24,618.86 |
| Coordinated Care - Ambetter Exchange | 4 | 7 | 8 | $48,771.86 |
| Blue Shield - Regence Medicare Managed Care Plan | 4 | 13 | 17 | $26,254.03 |
| Coordinated Care - Cascade Care Select Exchange | 4 | 4 | 7 | $20,215.56 |
| Blue Shield - Regence All Commercial Plans | 4 | 15 | 32 | $57,927.08 |

---

## 6. Key Observations

### Hospital System Effects
- **Providence/Swedish hospitals** (5 of 6) are part of the same health system. Despite this, their negotiated rates vary meaningfully across campuses.
- **PeaceHealth** is the only independent hospital in the dataset, making it the most important comparison point for corridor market analysis.

### Payer Negotiation Patterns
- **Medicare Advantage** payers (Aetna Medicare, UHC Medicare, Humana Medicare, etc.) cluster in a narrow band -- typically within 10-20% of each other across hospitals.
- **Commercial payers** (Aetna Commercial, Premera Commercial, Regence Commercial) show the widest hospital-to-hospital variation -- often 2-4x.
- **Medicaid Managed Care** (Molina, Coordinated Care) consistently has the lowest rates across all hospitals.

### Coverage Gaps
- CPT-level payer-negotiated rates are only available from PeaceHealth. Providence/Swedish publish CPT codes without payer-specific negotiated amounts.
- DRG-level analysis is the strongest basis for cross-hospital comparison in this dataset.
- Additional hospitals (particularly UW Medical Center and Overlake) would significantly strengthen market coverage.

---

## 7. Methodology

1. Parse heterogeneous MRF structures (JSON, CSV, ZIP)
2. Normalize code and code_type (MS-DRG -> DRG, HCPCS -> CPT where applicable)
3. Strict scope filter requires matching both code and code_type to the surgical catalog
4. Compute effective_price as negotiated_rate or cash_price fallback
5. Exclude zero and null prices
6. Confidence gating based on hospital count, rate count, and payer count thresholds

**Data sources:** Hospital machine-readable price transparency files as required by CMS Hospital Price Transparency Rule.

---

*Generated from public hospital machine-readable price transparency files. These are negotiated facility rates, not final patient bills.*
