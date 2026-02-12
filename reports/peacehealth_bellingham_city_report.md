# PeaceHealth St. Joseph (Bellingham) Patient-Focused Cost Report

Date: 2026-02-09
Project: `.`

## Why This Report Is For Bellingham Residents

This report focuses specifically on how surgical prices vary **inside PeaceHealth St. Joseph Medical Center** and what that likely means for local patients planning care.

## PeaceHealth Snapshot

- Scoped PeaceHealth records: **857**
- Distinct procedures in scope: **22**
- Distinct payer labels in scope: **29**
- Confidence mix for PeaceHealth-covered procedures: **14 HIGH, 6 LOW**

## What A Bellingham Patient Should Know First

1. Your insurance plan can change expected allowed amounts substantially, even at the same hospital.
2. For several procedures, payer spread is multi-x (not small percentage differences).
3. The transparency data are useful for negotiation and planning, but they are not a final bill quote.

## PeaceHealth Procedure Variation (Within-Hospital)

| code | code_type | description | n_payers | median_price | p90_p10_ratio | min_price | max_price |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 163 | DRG | Major chest procedures with MCC | 27 | $206,496.16 | 7.68x | $38,086.25 | $400,602.54 |
| 377 | DRG | GI hemorrhage with MCC | 27 | $55,000.65 | 6.17x | $12,587.14 | $128,525.73 |
| 49650 | CPT | Laparoscopic inguinal hernia repair | 23 | $8,838.26 | 6.17x | $2,378.69 | $62,976.28 |
| 472 | DRG | Cervical spinal fusion with CC | 27 | $85,819.01 | 5.02x | $16,305.05 | $166,488.88 |
| 481 | DRG | Hip and femur procedures except major joint with CC | 27 | $58,392.32 | 4.77x | $11,094.16 | $113,281.10 |
| 329 | DRG | Major small and large bowel procedures with MCC | 27 | $110,920.24 | 4.46x | $21,074.12 | $219,352.67 |
| 27447 | CPT | Total knee arthroplasty | 23 | $17,197.50 | 4.20x | $5,345.09 | $99,551.63 |
| 45378 | CPT | Colonoscopy diagnostic | 23 | $1,821.50 | 4.16x | $461.43 | $7,159.57 |
| 482 | DRG | Hip and femur procedures except major joint without CC/MCC | 27 | $36,854.50 | 4.13x | $7,002.11 | $71,497.74 |
| 473 | DRG | Cervical spinal fusion without CC/MCC | 27 | $53,802.60 | 4.09x | $10,222.14 | $104,377.04 |
| 480 | DRG | Hip and femur procedures except major joint with MCC | 27 | $57,160.00 | 3.61x | $10,370.09 | $119,728.11 |
| 216 | DRG | Cardiac valve and other major cardiothoracic procedures | 27 | $184,655.88 | 3.52x | $29,872.14 | $438,014.41 |
| 469 | DRG | Major joint replacement with MCC | 27 | $62,540.48 | 3.48x | $10,824.52 | $133,068.78 |
| 47562 | CPT | Laparoscopic cholecystectomy | 23 | $13,278.50 | 3.41x | $2,326.82 | $45,140.94 |
| 471 | DRG | Cervical spinal fusion with MCC | 27 | $92,935.44 | 3.40x | $15,468.92 | $197,740.68 |
| 27130 | CPT | Total hip arthroplasty | 23 | $28,001.38 | 3.36x | $6,324.51 | $99,551.63 |
| 743 | DRG | Uterine and adnexa procedures for non-malignancy | 27 | $21,401.24 | 3.31x | $3,629.66 | $48,799.08 |
| 483 | DRG | Major joint/limb reattachment of upper extremities | 27 | $45,214.33 | 3.30x | $7,670.02 | $103,737.22 |
| 267 | DRG | Endovascular cardiac valve replacement | 27 | $88,489.65 | 3.24x | $13,305.36 | $191,528.34 |
| 470 | DRG | Major joint replacement or reattachment of lower extremity | 27 | $35,917.43 | 3.15x | $5,796.19 | $67,911.94 |
| 29881 | CPT | Arthroscopy knee meniscectomy | 23 | $6,429.50 | 3.07x | $1,508.80 | $25,103.82 |
| 460 | DRG | Spinal fusion except cervical without CC/MCC | 15 | $116,497.44 | 2.22x | $19,391.12 | $198,000.41 |

Interpretation:
- `p90/p10` above ~2.0x means large payer-driven spread at this hospital for that procedure.
- `min_price`/`max_price` indicates the observed negotiated range in this dataset, not guaranteed patient liability.

## Biggest Payer Spread By Procedure (PeaceHealth)

| code | description | low_payer | low_median | high_payer | high_median | high_low_ratio |
| --- | --- | --- | --- | --- | --- | --- |
| 47562 | Laparoscopic cholecystectomy | Molina Healthcare of WA - Managed Medicaid | $2,326.82 | Regence Blue Shield - Commercial | $45,140.94 | 19.40x |
| 49650 | Laparoscopic inguinal hernia repair | Molina Healthcare of WA - Managed Medicaid | $2,378.69 | Regence Blue Shield - Commercial | $45,140.94 | 18.98x |
| 29881 | Arthroscopy knee meniscectomy | Molina Healthcare of WA - Managed Medicaid | $1,508.80 | Regence Blue Shield - Commercial | $25,103.82 | 16.64x |
| 27447 | Total knee arthroplasty | Molina Healthcare of WA - Managed Medicaid | $6,324.51 | Regence Blue Shield - Commercial | $99,551.63 | 15.74x |
| 27130 | Total hip arthroplasty | Molina Healthcare of WA - Managed Medicaid | $6,324.51 | Regence Blue Shield - Commercial | $99,551.63 | 15.74x |
| 216 | Cardiac valve and other major cardiothoracic procedures | Molina Healthcare of WA - Managed Medicaid | $29,872.14 | United Healthcare - All Payer Appendix | $438,014.41 | 14.66x |
| 267 | Endovascular cardiac valve replacement | Molina Healthcare of WA - Managed Medicaid | $13,305.36 | United Healthcare - All Payer Appendix | $191,528.34 | 14.39x |
| 483 | Major joint/limb reattachment of upper extremities | Molina Healthcare of WA - Managed Medicaid | $7,670.02 | United Healthcare - All Payer Appendix | $103,737.22 | 13.53x |
| 743 | Uterine and adnexa procedures for non-malignancy | Molina Healthcare of WA - Managed Medicaid | $3,629.66 | United Healthcare - All Payer Appendix | $48,799.08 | 13.44x |
| 471 | Cervical spinal fusion with MCC | Molina Healthcare of WA - Managed Medicaid | $15,468.92 | United Healthcare - All Payer Appendix | $197,740.68 | 12.78x |
| 469 | Major joint replacement with MCC | Molina Healthcare of WA - Managed Medicaid | $10,824.52 | United Healthcare - All Payer Appendix | $133,068.78 | 12.29x |
| 470 | Major joint replacement or reattachment of lower extremity | Molina Healthcare of WA - Managed Medicaid | $5,796.19 | United Healthcare - NexusACO | $67,911.94 | 11.72x |
| 480 | Hip and femur procedures except major joint with MCC | Molina Healthcare of WA - Managed Medicaid | $10,370.09 | United Healthcare - All Payer Appendix | $119,728.11 | 11.55x |
| 45378 | Colonoscopy diagnostic | Molina Healthcare of WA - Managed Medicaid | $656.46 | Regence Blue Shield - Commercial | $7,053.96 | 10.75x |
| 163 | Major chest procedures with MCC | Kaiser WA - All Other LOB | $38,086.25 | Humana Health Plan - Commercial | $400,602.54 | 10.52x |
| 329 | Major small and large bowel procedures with MCC | Molina Healthcare of WA - Managed Medicaid | $21,074.12 | Regence Blue Shield - Commercial | $219,352.67 | 10.41x |
| 482 | Hip and femur procedures except major joint without CC/MCC | Molina Healthcare of WA - Managed Medicaid | $7,002.11 | Humana Health Plan - Commercial | $71,497.74 | 10.21x |
| 460 | Spinal fusion except cervical without CC/MCC | Molina Healthcare of WA - Managed Medicaid | $19,391.12 | Humana Health Plan - Commercial | $198,000.41 | 10.21x |
| 473 | Cervical spinal fusion without CC/MCC | Molina Healthcare of WA - Managed Medicaid | $10,222.14 | Humana Health Plan - Commercial | $104,377.04 | 10.21x |
| 472 | Cervical spinal fusion with CC | Molina Healthcare of WA - Managed Medicaid | $16,305.05 | Humana Health Plan - Commercial | $166,488.88 | 10.21x |
| 481 | Hip and femur procedures except major joint with CC | Molina Healthcare of WA - Managed Medicaid | $11,094.16 | Humana Health Plan - Commercial | $113,281.10 | 10.21x |
| 377 | GI hemorrhage with MCC | Molina Healthcare of WA - Managed Medicaid | $12,587.14 | Humana Health Plan - Commercial | $128,525.73 | 10.21x |

Interpretation:
- `high_low_ratio` quantifies how far apart payer medians are for the same procedure at PeaceHealth.
- This is the clearest signal for patients that pre-op benefit checks matter.

## Which Payers Trend Lower vs Higher (PeaceHealth Relative Index)

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

Interpretation:
- A value below `1.00x` means that payer tends to be below the PeaceHealth procedure median.
- A value above `1.00x` means that payer tends to be above the PeaceHealth procedure median.

## Corridor Context: DRG 470 (Most Comparable Cross-Hospital Signal)

| hospital_name | n_rates | median_price | min_price | max_price |
| --- | --- | --- | --- | --- |
| Swedish Medical Center Issaquah | 1 | $16,551.83 | $16,551.83 | $16,551.83 |
| Swedish Edmonds | 4 | $16,942.32 | $13,373.82 | $54,293.44 |
| Providence Health And Services - Washington | 14 | $16,968.78 | $13,577.49 | $45,016.35 |
| Swedish Medical Center | 16 | $19,761.92 | $2,993.79 | $40,241.67 |
| PeaceHealth St Joseph Medical Center | 27 | $35,917.43 | $5,796.19 | $67,911.94 |

Interpretation:
- DRG 470 is currently the strongest cross-hospital comparison signal in this dataset.
- For most CPT procedures, current cross-hospital evidence is limited, so local patient decisions should emphasize within-PeaceHealth variation + insurer-specific benefits checks.

## What To Ask Before Scheduling Surgery In Bellingham

1. “Can you provide a written pre-op estimate with facility, surgeon, anesthesia, imaging/lab, and pathology components?”
2. “Which exact CPT/DRG codes are expected for my case, and inpatient vs outpatient setting?”
3. “Can you run an estimate under my exact plan benefits (deductible, coinsurance, out-of-pocket max status)?”
4. “Can I see both in-network negotiated estimate and cash/self-pay quote?”
5. “Are all involved clinicians and facilities in-network for my plan?”
6. “What prior authorization is required, and who is responsible for obtaining it?”

## Practical Bottom Line For Local Patients

- Use this report as a **financial planning and question checklist** before surgery.
- Do not rely on one headline number; request a full episode estimate.
- If your procedure is in a high-spread category, compare options and ask for itemized assumptions before committing.
