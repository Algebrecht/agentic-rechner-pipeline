from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple


BASE_DIR = Path(__file__).resolve().parent
INFO_DIR = BASE_DIR.parent / "info_from_excel"


@dataclass(frozen=True)
class TariffParameters:
    alpha: float
    beta: float
    gamma1: float
    gamma2: float
    stk: float
    stosatz: float
    tafel: str
    mrs: float


@dataclass(frozen=True)
class SurplusDeclaration:
    year: int
    ueb_beta: float
    ueb_ris: float
    ueb_gamma: float


@dataclass(frozen=True)
class CoursePoint:
    datum: date
    individual: float
    constant: float


def parse_excel_date(value: str) -> date:
    return date.fromisoformat(value.strip().split(" ")[0])


def excel_datetime_text(value: date) -> str:
    return f"{value.isoformat()} 00:00:00"


def _as_float(value: str) -> float:
    return float(str(value).strip())


def _read_sheet_rows(name: str) -> List[Dict[str, str]]:
    path = INFO_DIR / f"{name}.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


@lru_cache(maxsize=1)
def tariff_table() -> Dict[str, TariffParameters]:
    rows = _read_sheet_rows("Daten")
    by_addr = {row["Adresse"]: row["Wert"] for row in rows}
    columns = {
        "Einzeltarif": "B",
        "Kollektivtarif": "C",
        "Haustarif": "D",
    }
    out: Dict[str, TariffParameters] = {}
    for name, col in columns.items():
        out[name] = TariffParameters(
            alpha=_as_float(by_addr[f"${col}$17"]),
            beta=_as_float(by_addr[f"${col}$18"]),
            gamma1=_as_float(by_addr[f"${col}$19"]),
            gamma2=_as_float(by_addr[f"${col}$20"]),
            stk=_as_float(by_addr[f"${col}$21"]),
            stosatz=_as_float(by_addr[f"${col}$22"]),
            tafel=by_addr[f"${col}$23"],
            mrs=_as_float(by_addr[f"${col}$24"]),
        )
    return out


def get_tariff_parameters(tarifart: str) -> TariffParameters:
    try:
        return tariff_table()[tarifart]
    except KeyError as exc:
        raise ValueError(f"Unknown Tarifart: {tarifart!r}") from exc


def get_parm(tarifart: str, parameter: str):
    params = get_tariff_parameters(tarifart)
    key = parameter.lower()
    aliases = {
        "stk": "stk",
        "stks": "stk",
        "stosatz": "stosatz",
        "tafel": "tafel",
        "mrs": "mrs",
        "alpha": "alpha",
        "beta": "beta",
        "gamma1": "gamma1",
        "gamma2": "gamma2",
    }
    attr = aliases.get(key)
    if attr is None:
        raise ValueError(f"Unknown tariff parameter: {parameter!r}")
    return getattr(params, attr)


@lru_cache(maxsize=1)
def surplus_table() -> Tuple[SurplusDeclaration, ...]:
    rows = _read_sheet_rows("Daten")
    by_addr = {row["Adresse"]: row["Wert"] for row in rows}
    out: List[SurplusDeclaration] = []
    for excel_row in range(28, 33):
        out.append(
            SurplusDeclaration(
                year=int(_as_float(by_addr[f"$A${excel_row}"])),
                ueb_beta=_as_float(by_addr[f"$B${excel_row}"]),
                ueb_ris=_as_float(by_addr[f"$C${excel_row}"]),
                ueb_gamma=_as_float(by_addr[f"$D${excel_row}"]),
            )
        )
    return tuple(out)


def get_ueb(jahr: int, art: str) -> float:
    rows = surplus_table()
    max_year = max(row.year for row in rows)
    search_year = min(jahr, max_year)
    for row in rows:
        if row.year == search_year:
            if art == "Ü_beta":
                return row.ueb_beta
            if art == "Ü_ris":
                return row.ueb_ris
            if art == "Ü_gamma":
                return row.ueb_gamma
    raise ValueError(f"Unknown surplus declaration year: {jahr!r}")


@lru_cache(maxsize=1)
def course_points() -> Tuple[CoursePoint, ...]:
    rows = _read_sheet_rows("Kurse")
    points: List[CoursePoint] = []
    for row in rows:
        addr = row["Adresse"]
        if not addr.startswith("$A$"):
            continue
        excel_row = int(addr.replace("$A$", ""))
        if excel_row < 4:
            continue
        by_addr = {
            other["Adresse"]: other["Wert"]
            for other in rows
            if other["Adresse"].endswith(f"${excel_row}")
        }
        datum = parse_excel_date(row["Wert"])
        individual = _as_float(by_addr[f"$C${excel_row}"])
        constant = _as_float(by_addr[f"$D${excel_row}"])
        points.append(CoursePoint(datum=datum, individual=individual, constant=constant))
    return tuple(points)


def course_lookup(mode: str, performance: float) -> Dict[date, float]:
    points = course_points()
    if mode == "konstant":
        constant = points[0].constant
        out: Dict[date, float] = {points[0].datum: constant}
        factor = (1.0 + performance) ** (1.0 / 12.0)
        for point in points[1:]:
            constant = round(constant * factor, 5)
            out[point.datum] = constant
        return out
    return {point.datum: point.individual for point in points}


def get_kurs(datum: date, mode: str, performance: float) -> float:
    return course_lookup(mode, performance).get(datum, 99999.0)


def selected_course_values(mode: str, performance: float) -> Tuple[float, ...]:
    lookup = course_lookup(mode, performance)
    return tuple(lookup[point.datum] for point in course_points())


def constant_course_values(performance: float) -> Tuple[float, ...]:
    lookup = course_lookup("konstant", performance)
    return tuple(lookup[point.datum] for point in course_points())

