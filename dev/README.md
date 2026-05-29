# dev/ — interne Entwicklungs-Dokumentation

Arbeitsraum für **Change Requests (CR)**, Design-Notizen und Entscheidungs-
vorlagen. **Kein** Teil der Laufzeit-/Pipeline-Logik — reine Doku.

## Konventionen

- Change Requests: `CR-<NNN>-<kurz-slug>.md` (fortlaufend nummeriert).
- Jeder CR hat oben einen Status: `Vorschlag` → `In Abstimmung` → `Angenommen` /
  `Abgelehnt` / `Zurückgestellt`.
- Entscheidungen, die geteilte Settings/Module berühren (z. B. `pyproject.toml`,
  `qa/security.py`), werden mit dem Kreis (insb. Alexander) abgestimmt, bevor
  sie `Angenommen` werden.

## Index

- [CR-001](CR-001-llm-provider-subscription-auth.md) — LLM-Calls über
  Claude-Subscription-Auth (Agent SDK) statt gemeterter API zur Kostensenkung.
- [CR-002](CR-002-fixed-golden-master-harness.md) — fester, reviewter
  Golden-Master-Harness statt LLM-generiertem Test (löst Security-Idiom-Varianz,
  Orakel-Unabhängigkeit und halbiert die Kosten pro Lauf).
