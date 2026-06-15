from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Tuple

from commutation import Act_Altersberechnung, Act_qx, edate, excel_round
from inputs import ContractInputs, DEFAULT_CONTRACT
from params import (
    constant_course_values,
    excel_datetime_text,
    get_kurs,
    get_parm,
    get_ueb,
    selected_course_values,
)


DEFAULT_PROJECTION_MONTHS = 492


@dataclass(frozen=True)
class ProjectionRow:
    datum: date
    mon: int
    k: int
    t: int
    faellig: int
    b: float
    alpha: float
    beta: float
    ueb_beta: float
    p_k: float
    p_a: float
    p_ris: float
    ueb_ris: float
    k_gamma: float
    ueb_gamma: float
    dk_minus: float
    dk_plus: float
    euro_dk_minus: float
    euro_dk_plus: float
    tfl: float
    stoab: float
    rkw: float


@dataclass(frozen=True)
class CalculationResult:
    contract: ContractInputs
    x: int
    beisum: float
    mtsum: float
    mrsum: float
    abldat: date
    rows: Tuple[ProjectionRow, ...]


def calc_x(contract: ContractInputs) -> int:
    return Act_Altersberechnung(contract.gebdat, contract.begdat, "K")


def calc_beisum(contract: ContractInputs) -> float:
    return contract.beitrag * contract.zahlweise * contract.bzdauer


def calc_mtsum(contract: ContractInputs, beisum: float) -> float:
    return contract.mts * beisum


def calc_mrsum(contract: ContractInputs, beisum: float) -> float:
    return get_parm(contract.tarifart, "mrs") * beisum


def calc_abldat(contract: ContractInputs) -> date:
    return edate(contract.begdat, contract.dauer * 12 - 1)


def calc_k(mon: int) -> int:
    return mon // 12


def calc_t(mon: int) -> int:
    return mon % 12


def calc_faellig(mon: int, zahlweise: int) -> int:
    return 1 if mon % int(12 / zahlweise) == 0 else 0


def calc_b(contract: ContractInputs, k: int, faellig: int) -> float:
    return contract.beitrag * faellig * int(k < contract.bzdauer)


def calc_alpha(contract: ContractInputs, beisum: float, k: int, faellig: int) -> float:
    value = (
        get_parm(contract.tarifart, "alpha")
        / (2.0 * contract.zahlweise)
        * beisum
        * int(k < 2)
        * faellig
    )
    return excel_round(value, 2)


def calc_beta(contract: ContractInputs, b: float, faellig: int) -> float:
    return excel_round(b * get_parm(contract.tarifart, "beta") * faellig, 2)


def calc_ueb_beta(contract: ContractInputs, datum: date, b: float, faellig: int) -> float:
    return excel_round(b * get_ueb(datum.year, "Ü_beta") * faellig, 2)


def calc_p_k(alpha: float, beta: float) -> float:
    return alpha + beta


def calc_p_a(b: float, p_k: float, ueb_beta: float) -> float:
    return b - p_k + ueb_beta


def calc_dk_minus(previous_dk_plus: float, k: int, dauer: int, first: bool) -> float:
    if first:
        return 0.0
    return previous_dk_plus * int(k < dauer)


def calc_euro_dk_minus(dk_minus: float, kurs: float) -> float:
    return excel_round(dk_minus * kurs, 2)


def calc_p_ris(
    contract: ContractInputs,
    x: int,
    k: int,
    euro_dk_minus: float,
    p_a: float,
    mtsum: float,
    mrsum: float,
) -> float:
    risikosumme = max(mtsum - euro_dk_minus - p_a, mrsum)
    qx = Act_qx(
        x + k,
        contract.geschlecht,
        str(get_parm(contract.tarifart, "Tafel")),
        contract.gebdat.year,
        x + contract.dauer,
        1,
    )
    return excel_round(1.0 / 12.0 * risikosumme * qx, 2)


def calc_ueb_ris(datum: date, p_ris: float) -> float:
    return excel_round(p_ris * get_ueb(datum.year, "Ü_ris"), 2)


def calc_k_gamma(contract: ContractInputs, k: int, euro_dk_minus: float) -> float:
    parameter = "gamma1" if k < contract.bzdauer else "gamma2"
    return excel_round(euro_dk_minus * get_parm(contract.tarifart, parameter), 2)


def calc_ueb_gamma(datum: date, euro_dk_minus: float) -> float:
    return excel_round(euro_dk_minus * get_ueb(datum.year, "Ü_gamma"), 2)


def calc_dk_plus(
    contract: ContractInputs,
    datum: date,
    k: int,
    dk_minus: float,
    p_a: float,
    p_ris: float,
    k_gamma: float,
    ueb_ris: float,
    ueb_gamma: float,
) -> float:
    prev_kurs = get_kurs(edate(datum, -1), contract.kurse, contract.performance)
    increment = (p_a - p_ris - k_gamma - get_parm(contract.tarifart, "StK") + ueb_ris + ueb_gamma) / prev_kurs
    return excel_round(dk_minus + increment, 10) * int(k < contract.dauer)


def calc_euro_dk_plus(dk_plus: float, kurs: float) -> float:
    return excel_round(dk_plus * kurs, 2)


def calc_tfl(mtsum: float, euro_dk_minus: float, mrsum: float) -> float:
    return excel_round(max(mtsum, euro_dk_minus + mrsum), 2)


def calc_stoab(contract: ContractInputs, k: int) -> float:
    return (
        get_parm(contract.tarifart, "StoSatz")
        * (contract.dauer - k)
        * contract.beitrag
        * contract.zahlweise
        * int(k < contract.bzdauer)
    )


def calc_rkw(euro_dk_plus: float, stoab: float) -> float:
    return max(euro_dk_plus - stoab, 0.0)


def project_contract(
    contract: ContractInputs = DEFAULT_CONTRACT,
    months: int = DEFAULT_PROJECTION_MONTHS,
) -> CalculationResult:
    x = calc_x(contract)
    beisum = calc_beisum(contract)
    mtsum = calc_mtsum(contract, beisum)
    mrsum = calc_mrsum(contract, beisum)
    abldat = calc_abldat(contract)
    rows: List[ProjectionRow] = []
    previous_dk_plus = 0.0

    for mon in range(months):
        datum = contract.begdat if mon == 0 else edate(rows[-1].datum, 1)
        k = calc_k(mon)
        t = calc_t(mon)
        faellig = calc_faellig(mon, contract.zahlweise)
        b = calc_b(contract, k, faellig)
        alpha = calc_alpha(contract, beisum, k, faellig)
        beta = calc_beta(contract, b, faellig)
        ueb_beta = calc_ueb_beta(contract, datum, b, faellig)
        p_k = calc_p_k(alpha, beta)
        p_a = calc_p_a(b, p_k, ueb_beta)
        dk_minus = calc_dk_minus(previous_dk_plus, k, contract.dauer, mon == 0)
        kurs = get_kurs(datum, contract.kurse, contract.performance)
        euro_dk_minus = calc_euro_dk_minus(dk_minus, kurs)
        p_ris = calc_p_ris(contract, x, k, euro_dk_minus, p_a, mtsum, mrsum)
        ueb_ris = calc_ueb_ris(datum, p_ris)
        k_gamma = calc_k_gamma(contract, k, euro_dk_minus)
        ueb_gamma = calc_ueb_gamma(datum, euro_dk_minus)
        dk_plus = calc_dk_plus(
            contract,
            datum,
            k,
            dk_minus,
            p_a,
            p_ris,
            k_gamma,
            ueb_ris,
            ueb_gamma,
        )
        euro_dk_plus = calc_euro_dk_plus(dk_plus, kurs)
        tfl = calc_tfl(mtsum, euro_dk_minus, mrsum)
        stoab = calc_stoab(contract, k)
        rkw = calc_rkw(euro_dk_plus, stoab)
        rows.append(
            ProjectionRow(
                datum=datum,
                mon=mon,
                k=k,
                t=t,
                faellig=faellig,
                b=b,
                alpha=alpha,
                beta=beta,
                ueb_beta=ueb_beta,
                p_k=p_k,
                p_a=p_a,
                p_ris=p_ris,
                ueb_ris=ueb_ris,
                k_gamma=k_gamma,
                ueb_gamma=ueb_gamma,
                dk_minus=dk_minus,
                dk_plus=dk_plus,
                euro_dk_minus=euro_dk_minus,
                euro_dk_plus=euro_dk_plus,
                tfl=tfl,
                stoab=stoab,
                rkw=rkw,
            )
        )
        previous_dk_plus = dk_plus

    return CalculationResult(
        contract=contract,
        x=x,
        beisum=beisum,
        mtsum=mtsum,
        mrsum=mrsum,
        abldat=abldat,
        rows=tuple(rows),
    )


def _row_at(result: CalculationResult, datum: date) -> ProjectionRow:
    for row in result.rows:
        if row.datum == datum:
            return row
    raise ValueError(f"No projection row for {datum.isoformat()}")


def daten_scalars(result: CalculationResult) -> Dict[str, object]:
    row = _row_at(result, result.contract.dat_wertstand)
    return {
        "€DK-": row.euro_dk_plus,
        "€DK+": row.euro_dk_minus,
        "TFL": row.tfl,
        "RKW": row.rkw,
        "AblDat": excel_datetime_text(result.abldat),
    }


def kalkulation_scalars(result: CalculationResult) -> Dict[str, object]:
    first = result.rows[0]
    return {
        "x": float(result.x),
        "BeiSum": result.beisum,
        "MTSum": result.mtsum,
        "MRSum": result.mrsum,
        "Datum": excel_datetime_text(first.datum),
        "Pxt": first.p_a,
        "ratzu": float(first.faellig),
    }


def _fresh_projection_row(row: ProjectionRow) -> Dict[str, float]:
    return {
        "mon": float(row.mon),
        "k": float(row.k),
        "t": float(row.t),
        "fäll": float(row.faellig),
        "B": row.b,
        "alpha": row.alpha,
        "beta": row.beta,
        "Ü_beta": row.ueb_beta,
        "P_K": row.p_k,
        "P_A": row.p_a,
        "P_ris": row.p_ris,
        "Ü_ris": row.ueb_ris,
        "K_gamma": row.k_gamma,
        "Ü_gamma": row.ueb_gamma,
        "DK+": row.dk_plus,
        "€DK-": row.euro_dk_minus,
        "€DK+": row.euro_dk_plus,
        "TFL": row.tfl,
        "StoAb": row.stoab,
        "RKW": row.rkw,
    }


def kalkulation_table_values(result: CalculationResult) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = [_fresh_projection_row(row) for row in result.rows]
    for row in result.rows[1:]:
        rows.append({"0": row.dk_minus})
    return rows


def legacy_kalkulation_table_values(result: CalculationResult) -> List[Dict[str, float]]:
    out: List[Dict[str, float]] = []
    for row in result.rows[7:58]:
        out.append(
            {
                "Axn": float(row.mon),
                "axn": float(row.k),
                "axt": float(row.t),
                "kVx_bpfl": float(row.faellig),
                "kDRx_bpfl": row.b,
                "kVx_bfr": row.alpha,
                "kVx_MRV": row.beta,
                "flex. Phase": row.ueb_beta,
                "StoAb": row.p_k,
                "RKW": row.p_a,
                "VS_bfr": row.p_ris,
            }
        )
    return out


def kurse_table_values(contract: ContractInputs = DEFAULT_CONTRACT) -> List[Dict[str, float]]:
    selected = selected_course_values(contract.kurse, contract.performance)
    constants = constant_course_values(contract.performance)
    rows: List[Dict[str, float]] = [{"Kursdaten": value} for value in selected]
    rows.extend({"100": value} for value in constants[1:])
    return rows


def golden_master_payload(kalkulation_shape: str = "fresh") -> Dict[str, object]:
    result = project_contract()
    if kalkulation_shape == "legacy":
        kalk_table = legacy_kalkulation_table_values(result)
    else:
        kalk_table = kalkulation_table_values(result)
    return {
        "scalars": {
            "Daten": daten_scalars(result),
            "Kalkulation": kalkulation_scalars(result),
            "Kurse": {},
        },
        "tables": {
            "Daten": [],
            "Kalkulation": kalk_table,
            "Kurse": kurse_table_values(result.contract),
        },
    }

