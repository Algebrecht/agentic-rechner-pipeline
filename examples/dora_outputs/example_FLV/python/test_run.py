from __future__ import annotations

import csv
from pathlib import Path
from pprint import pprint

from actuarial import golden_master_payload, project_contract


BASE_DIR = Path(__file__).resolve().parent
INFO_DIR = BASE_DIR.parent / "info_from_excel"


def _kalkulation_shape() -> str:
    expected = INFO_DIR / "Kalkulation_table_values.csv"
    if not expected.exists():
        return "fresh"
    with expected.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
    if "Axn" in header and "mon" not in header:
        return "legacy"
    return "fresh"


def golden_master_outputs() -> dict:
    """Berechnete Werte für den Golden-Master-Vergleich."""
    return golden_master_payload(kalkulation_shape=_kalkulation_shape())


def main() -> None:
    result = project_contract()
    print("FLV projection")
    pprint(
        {
            "x": result.x,
            "BeiSum": result.beisum,
            "MTSum": result.mtsum,
            "MRSum": result.mrsum,
            "rows": len(result.rows),
            "first_DK+": result.rows[0].euro_dk_plus,
            "wertstand_RKW": next(
                row.rkw for row in result.rows if row.datum == result.contract.dat_wertstand
            ),
        }
    )


if __name__ == "__main__":
    main()

