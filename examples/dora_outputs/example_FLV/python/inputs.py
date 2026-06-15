from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ContractInputs:
    geschlecht: str
    gebdat: date
    tarifart: str
    begdat: date
    dauer: int
    bzdauer: int
    mts: float
    beitrag: float
    zahlweise: int
    kurse: str
    performance: float
    dat_wertstand: date


DEFAULT_CONTRACT = ContractInputs(
    geschlecht="M",
    gebdat=date(1969, 12, 12),
    tarifart="Einzeltarif",
    begdat=date(2000, 1, 1),
    dauer=30,
    bzdauer=20,
    mts=0.6,
    beitrag=300.0,
    zahlweise=12,
    kurse="real",
    performance=0.04,
    dat_wertstand=date(2018, 4, 1),
)

