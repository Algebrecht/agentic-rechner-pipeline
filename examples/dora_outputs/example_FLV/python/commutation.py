from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from typing import Dict, Tuple
from xml.etree import ElementTree


RUND_LX = 16
RUND_TX = 16
RUND_DX = 16
RUND_CX = 16
RUND_NX = 16
RUND_MX = 16
RUND_RX = 16
MAX_ALTER = 123

BASE_DIR = Path(__file__).resolve().parent
TAFELN_XML = BASE_DIR / "tafeln.xml"


def excel_round(value: float, digits: int = 0) -> float:
    quant = Decimal("1").scaleb(-digits)
    # Excel ROUND is decimal half-away-from-zero from the displayed formula
    # result. Normalize tiny binary float artifacts before Decimal quantizing.
    normalized = round(float(value), max(digits + 4, 12))
    return float(Decimal(str(normalized)).quantize(quant, rounding=ROUND_HALF_UP))


def edate(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    days_in_month = (
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    return date(year, month, min(start.day, days_in_month[month - 1]))


@lru_cache(maxsize=1)
def _mortality_tables() -> Dict[str, Dict[int, float]]:
    root = ElementTree.parse(TAFELN_XML).getroot()
    out: Dict[str, Dict[int, float]] = {}
    for table in root.findall("table"):
        table_id = table.attrib["id"]
        ages: Dict[int, float] = {}
        for qx in table.findall("qx"):
            ages[int(qx.attrib["age"])] = float(qx.attrib["value"])
        out[table_id] = ages
    return out


def _table_id(sex: str, tafel: str) -> str:
    sex_key = "M" if sex.upper() == "M" else "F"
    return f"{tafel.upper()}_{sex_key}"


def Act_qx(
    alter: int,
    sex: str,
    tafel: str,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> float:
    del gebjahr, rentenbeginnalter, schicht
    table_id = _table_id(sex, tafel)
    tables = _mortality_tables()
    if table_id not in tables:
        raise ValueError(f"Mortality table is not implemented: {table_id}")
    try:
        return tables[table_id][alter]
    except KeyError as exc:
        raise ValueError(f"Age {alter} missing in mortality table {table_id}") from exc


@lru_cache(maxsize=None)
def _v_lx(
    endalter: int,
    sex: str,
    tafel: str,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> Tuple[float, ...]:
    grenze = MAX_ALTER if endalter == -1 else endalter
    values = [0.0] * (grenze + 1)
    values[0] = 1_000_000.0
    for i in range(1, grenze + 1):
        values[i] = excel_round(
            values[i - 1]
            * (1.0 - Act_qx(i - 1, sex, tafel, gebjahr, rentenbeginnalter, schicht)),
            RUND_LX,
        )
    return tuple(values)


def Act_lx(
    alter: int,
    sex: str,
    tafel: str,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> float:
    return _v_lx(alter, sex, tafel, gebjahr, rentenbeginnalter, schicht)[alter]


@lru_cache(maxsize=None)
def _v_tx(
    endalter: int,
    sex: str,
    tafel: str,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> Tuple[float, ...]:
    grenze = MAX_ALTER if endalter == -1 else endalter
    lx = _v_lx(grenze, sex, tafel, gebjahr, rentenbeginnalter, schicht)
    values = [0.0] * (grenze + 1)
    for i in range(grenze):
        values[i] = excel_round(lx[i] - lx[i + 1], RUND_TX)
    return tuple(values)


def Act_tx(
    alter: int,
    sex: str,
    tafel: str,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> float:
    return _v_tx(alter, sex, tafel, gebjahr, rentenbeginnalter, schicht)[alter]


@lru_cache(maxsize=None)
def _v_Dx(
    endalter: int,
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> Tuple[float, ...]:
    grenze = MAX_ALTER if endalter == -1 else endalter
    lx = _v_lx(grenze, sex, tafel, gebjahr, rentenbeginnalter, schicht)
    v = 1.0 / (1.0 + zins)
    return tuple(excel_round(lx[i] * v**i, RUND_DX) for i in range(grenze + 1))


def Act_Dx(
    alter: int,
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> float:
    return _v_Dx(alter, sex, tafel, zins, gebjahr, rentenbeginnalter, schicht)[alter]


@lru_cache(maxsize=None)
def _v_Cx(
    endalter: int,
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> Tuple[float, ...]:
    grenze = MAX_ALTER if endalter == -1 else endalter
    tx = _v_tx(grenze, sex, tafel, gebjahr, rentenbeginnalter, schicht)
    v = 1.0 / (1.0 + zins)
    values = [0.0] * (grenze + 1)
    for i in range(grenze):
        values[i] = excel_round(tx[i] * v ** (i + 1), RUND_CX)
    return tuple(values)


def Act_Cx(
    alter: int,
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> float:
    return _v_Cx(alter, sex, tafel, zins, gebjahr, rentenbeginnalter, schicht)[alter]


@lru_cache(maxsize=None)
def _v_Nx(
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> Tuple[float, ...]:
    dx = _v_Dx(-1, sex, tafel, zins, gebjahr, rentenbeginnalter, schicht)
    values = [0.0] * (MAX_ALTER + 1)
    values[MAX_ALTER] = dx[MAX_ALTER]
    for i in range(MAX_ALTER - 1, -1, -1):
        values[i] = excel_round(values[i + 1] + dx[i], RUND_DX)
    return tuple(values)


def Act_Nx(
    alter: int,
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> float:
    return _v_Nx(sex, tafel, zins, gebjahr, rentenbeginnalter, schicht)[alter]


@lru_cache(maxsize=None)
def _v_Mx(
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> Tuple[float, ...]:
    cx = _v_Cx(-1, sex, tafel, zins, gebjahr, rentenbeginnalter, schicht)
    values = [0.0] * (MAX_ALTER + 1)
    values[MAX_ALTER] = cx[MAX_ALTER]
    for i in range(MAX_ALTER - 1, -1, -1):
        values[i] = excel_round(values[i + 1] + cx[i], RUND_MX)
    return tuple(values)


def Act_Mx(
    alter: int,
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> float:
    return _v_Mx(sex, tafel, zins, gebjahr, rentenbeginnalter, schicht)[alter]


@lru_cache(maxsize=None)
def _v_Rx(
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> Tuple[float, ...]:
    mx = _v_Mx(sex, tafel, zins, gebjahr, rentenbeginnalter, schicht)
    values = [0.0] * (MAX_ALTER + 1)
    values[MAX_ALTER] = mx[MAX_ALTER]
    for i in range(MAX_ALTER - 1, -1, -1):
        values[i] = excel_round(values[i + 1] + mx[i], RUND_RX)
    return tuple(values)


def Act_Rx(
    alter: int,
    sex: str,
    tafel: str,
    zins: float,
    gebjahr: int = 0,
    rentenbeginnalter: int = 0,
    schicht: int = 1,
) -> float:
    return _v_Rx(sex, tafel, zins, gebjahr, rentenbeginnalter, schicht)[alter]


def Act_Altersberechnung(gebdat: date, berdat: date, methode: str) -> int:
    method = "K" if methode == "K" else "H"
    if method == "K":
        return berdat.year - gebdat.year
    return int(berdat.year - gebdat.year + (berdat.month - gebdat.month + 5) / 12.0)


def Act_Abzugsglied(k: int, zins: float) -> float:
    out = 0.0
    if k > 0:
        for lauf in range(k):
            out += lauf / k / (1.0 + lauf / k * zins)
        out *= (1.0 + zins) / k
    return out
