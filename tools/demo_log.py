#!/usr/bin/env python3
"""
demo_log.py — menschen-lesbare Wiedergabe EINES Laufs aus seinen Artefakten.

Vollstaendig datengetrieben: Blattnamen, Variablen-/Funktionsnamen, Formeln,
Abweichungen werden aus den Dateien gelesen (info_from_excel/, generated/,
DEBUG_*). Die einzigen festen Annahmen sind die Verzeichnis-Struktur und die
sechs vertraglich fixierten Ausgabedateinamen (inputs/params/tafeln.xml/
commutation/actuarial/test_run). Kein API-Aufruf, kein Eingriff in die Pipeline.

Aufruf:  python3 tools/demo_log.py [--repo .] [--peek 4] [--no-color]
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

PHASES = [
    ("Auslesen", "Excel und VBA werden ohne Excel in Artefakte überführt"),
    ("Kontext", "Prompt und Eingaben für das Modell"),
    ("Erzeugen", "Das Modell schreibt den Rechenkern in Python"),
    ("Absichern", "Der erzeugte Code wird statisch geprüft"),
    ("Validieren", "Vergleich gegen die Excel-Originalwerte (Golden-Master)"),
]
DERIVED = ("_compressed.csv", "_table_values.csv", "_scalar.json")


class Style:
    def __init__(self, on: bool):
        e = (lambda c: c if on else "")
        self.b, self.dim = e("\033[1m"), e("\033[2m")
        self.g, self.r, self.c = e("\033[32m"), e("\033[31m"), e("\033[36m")
        self.x = e("\033[0m")


def de_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def de_num(s: str) -> str:
    s = (s or "").strip()
    try:
        f = float(s)
    except ValueError:
        return s
    if f == int(f) and abs(f) < 1e15:
        return de_int(int(f))
    return f"{f:.6g}".replace(".", ",")


def lines_of(path: Path, n: int | None = None) -> list[str]:
    try:
        ls = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return ls if n is None else ls[:n]


def sheet_csvs(info: Path) -> list[Path]:
    return [p for p in sorted(info.glob("*.csv"))
            if p.name != "names_manager.csv" and not p.name.endswith(DERIVED)]


def read_names(info: Path) -> list[dict]:
    nm = info / "names_manager.csv"
    if not nm.exists():
        return []
    with nm.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def read_formulas(info: Path) -> list[tuple[str, str, str, str]]:
    out = []
    for sheet in sheet_csvs(info):
        with sheet.open(encoding="utf-8", newline="") as f:
            for r in csv.reader(f, delimiter=";"):
                if len(r) >= 4 and r[2].startswith("="):
                    out.append((r[0], r[1], r[2], r[3]))
    return out


def gen_functions(gen: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in sorted(gen.glob("*.py")):
        defs = re.findall(r"^def (\w+)", p.read_text(encoding="utf-8", errors="replace"), re.M)
        if defs:
            out[p.name] = defs
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--peek", type=int, default=3)
    ap.add_argument("--no-color", action="store_true")
    ns = ap.parse_args()

    repo = Path(ns.repo).resolve()
    info, gen, peek = repo / "info_from_excel", repo / "generated", ns.peek
    on = not ns.no_color and sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    s = Style(on)
    sys.path[:0] = [str(repo / "src"), str(gen)]

    width = 64
    excel = next(iter(repo.glob("examples/*.xlsm")), None)
    print(f"{s.b}{'=' * width}{s.x}")
    print(f"{s.b}  Rechenkern-Pipeline — Wiedergabe eines Laufs{s.x}")
    if excel:
        print(f"{s.dim}  Beispiel: {excel.name}   (Replay aus Lauf-Artefakten){s.x}")
    print(f"{s.b}{'=' * width}{s.x}")

    def phase(i: int):
        name, desc = PHASES[i]
        bar = "-" * max(3, width - 14 - len(name))
        print(f"\n{s.b}--[ {i + 1}/{len(PHASES)} ] {name} {bar}{s.x}")
        print(f"{s.dim}   {desc}{s.x}")

    _read(phase, info, peek, s)
    _context(phase, repo, info, s)
    _generate(phase, gen, info, s)
    _secure(phase, gen, s)
    _validate(phase, info, gen, peek, s)
    print()
    return 0


def _read(phase, info: Path, peek: int, s: Style):
    phase(0)
    formulas = read_formulas(info)
    if formulas:
        # kurze, gut lesbare Formeln bevorzugen
        readable = sorted(formulas, key=lambda x: len(x[2]))
        print(f"  {s.b}Beispiel-Formeln{s.x} ({min(peek, len(formulas))} von {len(formulas)}):")
        for _sheet, addr, formel, wert in readable[:peek]:
            a = addr.replace("$", "")
            print(f"    {a:5} {formel:<42}  ->  {de_num(wert)}")
    params = [(r["Name"], r.get("ValueEvaluated", "")) for r in read_names(info)
              if (r.get("ValueEvaluated") or "").strip() and not r["Name"].startswith("_xl")]
    if params:
        shown = "   ".join(f"{n} = {de_num(v)}" for n, v in params[:5])
        print(f"  {s.b}Benannte Größen{s.x} ({len(params)}): {shown} ...")
    vdir = info / "vba"
    vba = sorted(vdir.glob("*.txt")) if vdir.is_dir() else []
    if vba:
        big = max(vba, key=lambda p: p.stat().st_size)
        nl = len(lines_of(big))
        print(f"  {s.b}VBA-Module{s.x} ({len(vba)}): "
              + ", ".join(p.stem for p in vba) + f"   (z. B. {big.stem}: {nl} Zeilen)")
    nsc = sum(len([v for v in json.loads(p.read_text()).values() if v is not None])
              for p in info.glob("*_scalar.json"))
    ntab = 0
    for p in info.glob("*_table_values.csv"):
        with p.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            ntab += sum(1 for row in rd for c in row if (row.get(c) or "").strip())
    print(f"  {s.g}Ergebnis:{s.x} {nsc} Skalar- und {ntab} Tabellen-Erwartungswerte abgeleitet")


def _context(phase, repo: Path, info: Path, s: Style):
    phase(1)
    p = repo / "DEBUG_first_llm_prompt.txt"
    if p.exists():
        text = p.read_text(encoding="utf-8", errors="replace")
        print(f"  {s.b}Auftrag an das Modell{s.x} ({de_int(len(text))} Zeichen, Auszug):")
        shown = 0
        for ln in text.splitlines():
            t = ln.strip().strip("*# ").strip()
            if len(t) > 3 and t != "---":
                print(f"    {s.dim}|{s.x} {t[:72]}")
                shown += 1
            if shown >= 4:
                break
    manifest = info / "export_manifest.json"
    inputs = []
    if manifest.exists():
        try:
            inputs = [Path(q) for q in json.loads(manifest.read_text()).get("llm_inputs", [])]
        except (OSError, json.JSONDecodeError):
            inputs = []
    if not inputs:
        inputs = sheet_csvs(info) + [info / "names_manager.csv"]
    listing = ", ".join(f"{q.name} ({max(1, q.stat().st_size // 1024)} KB)"
                        for q in inputs if q.exists())
    print(f"  {s.b}Eingaben an das Modell{s.x} ({len(inputs)}): {listing}")


def _generate(phase, gen: Path, info: Path, s: Style):
    phase(2)
    files = [p for p in sorted(gen.glob("*.py")) + sorted(gen.glob("*.xml"))]
    if files:
        print(f"  {s.b}Erzeugte Dateien{s.x} ({len(files)}):")
        for p in files:
            print(f"    {p.name:18} {len(lines_of(p)):4} Zeilen")
    funcs = gen_functions(gen)
    for fname, defs in funcs.items():
        if fname == "actuarial.py" or (len(defs) >= 3 and fname not in ("test_run.py",)):
            print(f"  {s.b}{fname} — Funktionen{s.x} ({len(defs)}): {', '.join(defs[:8])}")
            break
    _correspondence(gen, info, s, funcs)


def _correspondence(gen: Path, info: Path, s: Style, funcs: dict[str, list[str]]):
    all_defs = {d: f for f, ds in funcs.items() for d in ds}
    scalars: list[str] = []
    for p in sorted(info.glob("*_scalar.json")):
        scalars += [k for k, v in json.loads(p.read_text()).items() if v is not None]
    names = {r["Name"]: r for r in read_names(info)}
    formulas = {a.replace("$", ""): (f, w) for _sh, a, f, w in read_formulas(info)}
    for name in scalars:
        row = names.get(name)
        if not row:
            continue
        cell = (row.get("RefersTo") or "").split("!")[-1].replace("=", "").replace("$", "")
        if cell not in formulas:
            continue
        func = next((d for d in all_defs if name.lower() in d.lower()), None)
        if not func:
            continue
        formel, wert = formulas[cell]
        if len(formel) > 46:
            continue  # nur gut lesbare Beispiele
        print(f"  {s.b}Beispiel Excel -> Python{s.x} (automatisch gewählt):")
        print(f"    {s.dim}Excel: {s.x} {name} ({cell})  {formel}   = {de_num(wert)}")
        sig = _signature(gen / all_defs[func], func)
        print(f"    {s.dim}Python:{s.x} {sig}")
        return


def _signature(path: Path, func: str) -> str:
    m = re.search(rf"^def {re.escape(func)}\([^)]*\)[^:]*:", path.read_text(encoding="utf-8"), re.M)
    return m.group(0) if m else f"def {func}(...)"


def _secure(phase, gen: Path, s: Style):
    phase(3)
    pys = sorted(gen.glob("*.py"))
    try:
        from rechner_pipeline.qa.security import scan_python_paths
        v = scan_python_paths(pys)
        if v:
            print(f"  {s.r}{len(v)} Befund(e){s.x} in {len(pys)} Dateien:")
            for x in v[:5]:
                print(f"    {Path(x.path).name}:{x.line} {x.category} {x.symbol}")
        else:
            print(f"  {s.g}Ergebnis:{s.x} {len(pys)} Dateien geprüft, keine gefährlichen "
                  f"Aufrufe (kein os.system / subprocess / Netz / Schreib-open)")
    except Exception as exc:  # noqa: BLE001
        print(f"  {s.dim}(Security-Scanner nicht verfügbar: {exc}){s.x}")


def _first_attempt(gen: Path):
    p = gen / "agentic_diagnostics.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    for diag in d.get("diagnostics", []):
        if diag.get("step") != "compare":
            continue
        for art in diag.get("artifacts", []):
            j = art.get("json")
            if isinstance(j, dict) and isinstance(j.get("stdout"), str):
                n, devs = 0, []
                for ln in j["stdout"].splitlines():
                    t = ln.strip()
                    if t.startswith("ABWEICHUNG:"):
                        devs.append(t.replace("ABWEICHUNG:", "").strip())
                    m = re.match(r"Abweichungen:\s*(\d+)", t)
                    if m:
                        n = int(m.group(1))
                return n, devs
    return None


def _validate(phase, info: Path, gen: Path, peek: int, s: Style):
    phase(4)
    first = _first_attempt(gen)
    if first:
        n, devs = first
        print(f"  {s.b}Durchlauf 1{s.x} — der erzeugte Rechenkern gegen die Excel-Werte:")
        for d in devs[:peek]:
            print(f"    {s.r}abweichend:{s.x} {d}")
        print(f"  {s.r}-> {n} Abweichung(en) — Durchlauf 1 nicht bestanden{s.x}")
        print(f"\n  {s.b}{s.c}Korrekturschleife{s.x} {s.dim}(die eigentliche agentische Intelligenz){s.x}")
        print("    Die Abweichungen werden dem Modell als zusätzlicher Kontext zurückgegeben;")
        prompt = gen.parent / "DEBUG_first_llm_prompt.txt"
        if prompt.exists():
            t = prompt.read_text(encoding="utf-8", errors="replace")
            extra = ", inkl. der Abweichungen" if "repair" in t.lower() else ""
            print(f"    der Workflow springt zurück zu [2] Kontext (Prompt nun "
                  f"{de_int(len(t))} Zeichen{extra})")
        print(f"    und durchläuft erneut  {s.b}[3] Erzeugen -> [4] Absichern -> [5] Validieren{s.x}")
        head = "Durchlauf 2: "
    else:
        head = ""
    try:
        from rechner_pipeline.qa.golden_master import compare, load_expected
        import test_run
        rep = compare(load_expected(info), test_run.golden_master_outputs())
        total = rep.scalars_tested + rep.table_cells_tested
        if rep.ok:
            print(f"\n  {s.b}{s.g}-> {head}{de_int(total)} von {de_int(total)} Werten "
                  f"stimmen mit dem Excel-Original{s.x}")
        else:
            print(f"\n  {s.b}{s.r}-> {head}{len(rep.deviations)} Abweichung(en) "
                  f"von {de_int(total)} Werten{s.x}")
            for d in rep.deviations[:peek]:
                print(f"    {d}")
        return
    except Exception:  # noqa: BLE001
        pass
    res = gen / "test_run_advanced_result.json"
    if res.exists():
        out = json.loads(res.read_text()).get("stdout", "")
        for ln in out.splitlines():
            if any(t in ln for t in ("BESTANDEN", "Abweichung", "RESULT")):
                print(f"    {ln.strip()}")


if __name__ == "__main__":
    raise SystemExit(main())
