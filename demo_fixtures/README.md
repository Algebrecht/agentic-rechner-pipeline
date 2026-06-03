# demo_fixtures — vorbereitete Modell-Ausgaben für den Replay-Provider

Diese `*_iteration.txt` sind komplette Modell-Ausgaben (FILE_START/END-Bloecke)
fuer den `--provider replay`. Damit laesst sich der **echte** Pipeline-Workflow
inkl. agentischer Korrekturschleife **kostenfrei und wiederholbar** vorfuehren —
ohne API-Aufruf.

Die drei Dateien sind aus einem echten Lauf abgeleitet; die ersten beiden lassen
gezielt Skalare im Golden-Master-Vertrag weg, sodass echte Abweichungen
entstehen, die die Schleife real korrigiert:

- `01_iteration.txt` — Skalare `Bxt` und `Pxt` fehlen  -> 2 Abweichungen
- `02_iteration.txt` — Skalar `Pxt` fehlt              -> 1 Abweichung
- `03_iteration.txt` — vollstaendig                    -> 0 Abweichungen (bestanden)

## Vorfuehren (mit Workflow-Logger)

    RP_WFLOG=1 RP_REPLAY_DIR=demo_fixtures \
      python agentic_pipeline.py --provider replay --test-mode fixed --max_retries_main 2

`RP_WFLOG=1` schaltet den menschen-lesbaren Workflow-Log ein (sonst laeuft die
Pipeline normal/technisch). Der Replay-Provider gibt die Dateien in Reihenfolge
zurueck; jeder agentische Durchlauf nimmt die naechste.
