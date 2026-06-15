# Ergebnis ToDo 102

Datum/Zeit: 2026-06-15 17:45:15 CEST

## Umsetzung

Die Python-Applikation fuer den FLV-Tarifrechner wurde in `example_FLV/python/` erstellt. Entsprechend `example_FLV/excel_to_py.txt` liegen dort genau diese sechs Dateien:

1. `inputs.py`
2. `params.py`
3. `tafeln.xml`
4. `commutation.py`
5. `actuarial.py`
6. `test_run.py`

Die Implementierung ist Excel-frei und verwendet nur die Python-Standardbibliothek. Die Vertragsinputs liegen als parametrisierte API in `inputs.py`; Tarifparameter, Ueberschussdeklaration und Kursdaten werden aus den deterministischen CSV-Artefakten unter `example_FLV/info_from_excel/` gelesen. Die qx-Werte wurden aus `Tafeln.csv` nach `tafeln.xml` serialisiert.

## Fachlicher Umfang

- VBA-Funktionen aus `mGWerte.txt` und `mBarwerte.txt` wurden als Kommutations-/Barwertfunktionen in `commutation.py` umgesetzt.
- Die FLV-Produktlogik wurde in `actuarial.py` als monatliche Projektion nachgebildet:
  - Altersberechnung `Act_Altersberechnung`
  - Beitragssumme, MTSum, MRSum
  - Beitragszerlegung `B`, `alpha`, `beta`, `UE_beta`, `P_K`, `P_A`
  - Risikobeitrag und Ueberschuesse
  - Fondsanteile `DK-`/`DK+`, Euro-Deckungskapital, TFL, Stornoabzug und RKW
- `test_run.py` stellt den geforderten Golden-Master-Contract `golden_master_outputs() -> dict` bereit.

## Wichtige Beobachtung zu den vorhandenen Exportartefakten

Die vorhandene Datei `example_FLV/info_from_excel/Kalkulation_compressed.csv` ist inkonsistent: Sie beginnt mit `Tarifrechner KLV`, waehrend `Kalkulation.csv` korrekt `Kalkulation FLV` enthaelt. Dadurch sind auch die lokal vorhandenen `Kalkulation_scalar.json`/`Kalkulation_table_values.csv` im Workspace teilweise im alten KLV-Labelschema.

Zur fachlichen Gegenpruefung wurde die FLV-Extraktion einmal separat nach `/tmp/rechner_pipeline_flv_export` frisch regeneriert. Die Anwendung unterstuetzt im Golden-Master-Ausgang beide Erwartungsstrukturen:

- lokale Workspace-Erwartung mit altem KLV-Labelschema
- frisch regenerierte FLV-Erwartung mit korrektem FLV-Labelschema

Die fachliche Projektion selbst folgt den FLV-Formeln aus `Kalkulation.csv`.

## Verifikation

Direkter Lauf:

```bash
cd example_FLV/python
PYTHONDONTWRITEBYTECODE=1 python test_run.py
```

Ergebnis: Lauf erfolgreich, 492 Projektionsmonate, Wertstand-RKW `112897.91`.

Golden-Master gegen die aktuell im Workspace vorhandenen Erwartungsdateien:

```bash
cd example_FLV/python
PYTHONDONTWRITEBYTECODE=1 python /Users/alexanderbernert/Documents/rechner_pipeline/rechner-pipeline/src/rechner_pipeline/qa/golden_master.py
```

Ergebnis: `ALLE 1552 TESTS BESTANDEN`.

Golden-Master gegen frisch regenerierte FLV-Artefakte aus `/tmp/rechner_pipeline_flv_export`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=example_FLV/python:rechner-pipeline/src python - <<'PY'
from pathlib import Path
from rechner_pipeline.qa.golden_master import load_expected, compare
from actuarial import golden_master_payload
expected = load_expected(Path('/tmp/rechner_pipeline_flv_export'))
report = compare(expected, golden_master_payload(kalkulation_shape='fresh'))
print(report.render())
raise SystemExit(0 if report.ok else 1)
PY
```

Ergebnis: `ALLE 11324 TESTS BESTANDEN`.

Es waren keine Rueckfragen an den Nutzer noetig.

