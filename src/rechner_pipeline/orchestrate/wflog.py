"""
Schlanker Workflow-Logger: die Pipeline gibt ihren tatsächlichen Verlauf
live aus (stdout). Die Inhalte kommen aus den Aufruf-Stellen (echte Daten),
dieses Modul formatiert nur.

Standardmäßig AUS (kein Output, kein Verhaltenswechsel). Aktivierung über
Umgebungsvariable ``RP_WFLOG=1`` oder ``enable()``.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Iterable

_ON = bool(os.environ.get("RP_WFLOG"))
_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

# Mitschrift: der Log wird zusätzlich in eine Datei geschrieben, damit der
# Verlauf des letzten Laufs ohne erneuten (API-)Lauf ansehbar ist. Datei wird
# beim ersten Schreiben angelegt/geleert. Pfad via RP_WFLOG_FILE.
_FILE_PATH = os.environ.get("RP_WFLOG_FILE", "DEBUG_workflow_log.txt")
_FILE = None  # lazily geöffnet; False = Öffnen fehlgeschlagen
_ANSI = re.compile(r"\033\[[0-9;]*m")


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
    if not _ON:
        return
    print(line, flush=True)
    global _FILE
    if _FILE is None:
        try:
            _FILE = open(_FILE_PATH, "w", encoding="utf-8")
        except OSError:
            _FILE = False
    if _FILE:
        _FILE.write(_ANSI.sub("", line) + "\n")
        _FILE.flush()


def phase(name: str, detail: str = "") -> None:
    """Beginn eines Workflow-Schritts."""
    _emit(f"\n{_B}{_C}* {name}{_X}" + (f"  {_DIM}{detail}{_X}" if detail else ""))


def detail(text: str) -> None:
    """Eine inhaltliche Zeile innerhalb eines Schritts."""
    _emit(f"    {text}")


def code(line: str) -> None:
    """Eine wörtliche Quellcode-Zeile (eingerückt, gedimmt)."""
    _emit(f"      {_DIM}| {line}{_X}")


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
