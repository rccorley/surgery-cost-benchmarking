from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw = root / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    demo = pd.DataFrame(
        [
            ["PeaceHealth St. Joseph Medical Center", "Premera", "27447", "CPT", "Total knee arthroplasty", 28000],
            ["PeaceHealth St. Joseph Medical Center", "Aetna", "27447", "CPT", "Total knee arthroplasty", 32500],
            ["Skagit Valley Hospital", "Premera", "27447", "CPT", "Total knee arthroplasty", 24500],
            ["Providence Regional Medical Center Everett", "Premera", "27447", "CPT", "Total knee arthroplasty", 37100],
            ["PeaceHealth St. Joseph Medical Center", "Regence", "45378", "CPT", "Colonoscopy diagnostic", 2600],
            ["Swedish Edmonds Campus", "Regence", "45378", "CPT", "Colonoscopy diagnostic", 1900],
            ["UW Medical Center Northwest Campus", "Aetna", "45378", "CPT", "Colonoscopy diagnostic", 4200],
            ["Cascade Valley Hospital", "Aetna", "47562", "CPT", "Laparoscopic cholecystectomy", 10800],
            ["PeaceHealth St. Joseph Medical Center", "Aetna", "47562", "CPT", "Laparoscopic cholecystectomy", 14900],
            ["Skagit Valley Hospital", "Regence", "47562", "CPT", "Laparoscopic cholecystectomy", 9800],
        ],
        columns=["hospital_name", "payer_name", "code", "code_type", "description", "negotiated_rate"],
    )

    demo.to_csv(raw / "demo_prices.csv", index=False)
    print("Wrote", raw / "demo_prices.csv")


if __name__ == "__main__":
    main()
