# CR-001 — LLM-Calls über Claude-Subscription-Auth (Agent SDK) statt gemeterter API

- **Status:** Vorschlag (Entscheidung offen)
- **Datum:** 2026-05-29
- **Branch-Kontext:** `feat/anthropic-provider`
- **Betroffen:** `src/rechner_pipeline/generate/client.py` (Provider/Auth), `src/rechner_pipeline/cli.py`
- **Abstimmung:** mit Alexander / Kreis (Kosten- und Auth-Governance)

## 1. Kontext / Problem

Jeder vollständige End-to-End-Lauf (`python pipeline.py --provider anthropic`)
kostet aktuell **~0,50 USD** über die gemeterte Anthropic-API
(`ANTHROPIC_API_KEY`, pro Token). Bei häufiger Iteration während der Entwicklung
summiert sich das. Frage: Lassen sich die LLM-Aufrufe über die vorhandene
**Claude-Subscription** (OAuth/Agent SDK) abrechnen statt pro Token?

## 2. Befund (Recherche, Stand 2026-05-29 — teils zu verifizieren)

- Das **Claude Agent SDK** (früher „Claude Code SDK") unterstützt seit
  **2026-06-15** Subscription-Billing via OAuth. Es zieht aus einem **separaten
  Monats-Kontingent** (Pro ~$20, Max ~$100–200), **nicht** pro Token.
- **Headless/CI:** einmalig `claude setup-token` (auf Maschine mit Browser) →
  `ANTHROPIC_AUTH_TOKEN` exportieren (Token ~1 Jahr gültig).
- **Auth-Vorrang:** `ANTHROPIC_API_KEY` **überschreibt** die Subscription →
  für Subscription-Nutzung darf der Key **nicht** gesetzt sein.
- **ToS:** für individuelle Dev-Automation zulässig; für geteilte Produktion
  empfiehlt Anthropic weiterhin den API-Key (planbare pay-as-you-go-Abrechnung).
- **Rate-Limits:** entsprechen den üblichen API-Tier-Limits.

## 3. Haken für genau diese Pipeline

Das Agent SDK exponiert (laut Recherche, **noch zu verifizieren**) die
Low-Level-Parameter **nicht**, auf die diese Pipeline angewiesen ist:

- **`max_output_tokens`** — war unser Truncation-Fix (16k → 32k). Ohne diesen
  Knopf droht erneut „Antwort mitten in `actuarial.py` abgeschnitten" — **ohne
  Gegenmittel**.
- **Modellwahl** (Sonnet ↔ Opus) und **Extended Thinking** (`reasoning_effort`)
  ebenfalls eingeschränkt.

Ein simples Umbiegen des LLM-Calls aufs Agent SDK würde also Kontrolle kosten,
die der Workflow real braucht.

## 4. Optionen

| Option | Beschreibung | Kosten | Kontrolle | Risiko |
|---|---|---|---|---|
| **A — Status quo** | Anthropic-API + `ANTHROPIC_API_KEY` (heute) | ~0,50/Lauf | voll (model/max_tokens/thinking) | keins |
| **B — Agent-SDK-Provider** | neuer `--provider claude-agent` über Agent SDK + Subscription | Monats-Kontingent | **eingeschränkt** | Truncation ohne max_tokens-Knopf |
| **C — Best-of-both (unverifiziert)** | bestehende `messages.stream`-Integration behalten, Auth via `ANTHROPIC_AUTH_TOKEN` gegen Subscription | Monats-Kontingent | voll | hängt davon ab, ob Standard-SDK gegen Subscription abrechnet |

## 5. Offene Fragen / zu verifizieren (vor Umsetzung)

1. Kann das Agent SDK in aktueller Version **doch** `model` / `max_output_tokens`
   / `thinking` setzen? (Versions-/Doku-Check.)
2. **Kernfrage für Option C:** Rechnet der Standard-`anthropic`-SDK mit gesetztem
   `ANTHROPIC_AUTH_TOKEN` (ohne `ANTHROPIC_API_KEY`) tatsächlich gegen die
   **Subscription** ab — oder ist OAuth-Billing dem Agent SDK / der `claude`-CLI
   vorbehalten? **Dies entscheidet, ob C überhaupt existiert.**
3. **Secret-Modell:** `ANTHROPIC_API_KEY_FILE` entfällt im Subscription-Modus;
   stattdessen `ANTHROPIC_AUTH_TOKEN`. Sauber wäre, die bestehende
   `*_FILE`-Pointer-Konvention (`resolve_api_key`) auf `ANTHROPIC_AUTH_TOKEN_FILE`
   zu erweitern (Token bleibt in restriktiver Host-Datei, vgl.
   [[feedback-secrets-file-pointer]]).
4. Verhalten/Backoff bei Rate-Limits im Pipeline-Kontext.

## 6. Empfehlung

- **Jetzt (Endphase der Iteration):** **Option A** beibehalten — der Umbau lohnt
  bei ~0,50/Lauf und nahezu fertiger Mechanik nicht.
- **Bei Dauer-/Vielnutzung:** **zuerst Option C verifizieren** (Frage 2) — sie
  behält die volle Steuerung. Trägt C nicht, dann **B nur**, wenn die
  `max_output_tokens`-Steuerung gesichert ist (sonst Truncation-Risiko).
- In jedem Fall mit Alexander/Kreis abstimmen (Kosten-/Auth-Governance,
  geteilte vs. individuelle Nutzung).

## 7. Referenzen

- Use the Claude Agent SDK with your Claude plan — https://support.claude.com/en/articles/15036540
- Agent SDK overview — https://code.claude.com/docs/en/agent-sdk/overview
- API rate limits — https://platform.claude.com/docs/en/api/rate-limits
