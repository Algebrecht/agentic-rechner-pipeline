"""
Schlanker Workflow-Logger: die Pipeline gibt ihren tatsächlichen Verlauf
live aus (stdout). Die Inhalte kommen aus den Aufruf-Stellen (echte Daten),
dieses Modul formatiert nur.

Standardmäßig AUS (kein Output, kein Verhaltenswechsel). Aktivierung über
Umgebungsvariable ``RP_WFLOG=1`` oder ``enable()``.
"""

from __future__ import annotations

import os
import sys
from typing import Iterable

_ON = bool(os.environ.get("RP_WFLOG"))
_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def enable(on: bool = True) -> None:
    global _ON
    _ON = on


def enabled() -> bool:
    return _ON


def _c(code: str) -> str:
    return code if (_ON and _COLOR) else ""


_B, _DIM, _G, _R, _C, _X = (
    _c("\033[1m"), _c("\033[2m"), _c("\033[32m"), _c("\033[31m"), _c("\033[36m"), _c("\033[0m"),
)


def _emit(line: str = "") -> None:
    if _ON:
        print(line, flush=True)


def phase(name: str, detail: str = "") -> None:
    """Beginn eines Workflow-Schritts."""
    _emit(f"\n{_B}{_C}* {name}{_X}" + (f"  {_DIM}{detail}{_X}" if detail else ""))


def detail(text: str) -> None:
    """Eine inhaltliche Zeile innerhalb eines Schritts."""
    _emit(f"    {text}")


def items(label: str, values: Iterable[str], limit: int = 4) -> None:
    """Auszug einer Liste (Auszug + Gesamtzahl)."""
    vals = list(values)
    if not vals:
        return
    shown = ", ".join(str(v) for v in vals[:limit])
    more = f"  (+{len(vals) - limit})" if len(vals) > limit else ""
    _emit(f"    {label}: {shown}{more}")


def iteration(n: int, text: str = "") -> None:
    """Start einer Schleifen-Iteration (z. B. agentischer Repair-Durchlauf)."""
    _emit(f"\n{_B}-- Iteration {n} --{_X}" + (f"  {_DIM}{text}{_X}" if text else ""))


def ok(text: str) -> None:
    _emit(f"  {_G}-> {text}{_X}")


def fail(text: str) -> None:
    _emit(f"  {_R}-> {text}{_X}")
