# Execution Flow

## Kroki wykonania taska

1. **Accept** — przyjęcie `TaskContract`.
2. **Preprocess** — normalizacja payloadu i metadanych.
3. **Choose strategy** — `structured` jeśli jest `output_schema`, inaczej `text`.
4. **Inference** — wywołanie providera z retry + timeout wg `ExecutionPolicy`.
5. **Repair** — uzupełnienie brakujących pól wymaganych przez schemat.
6. **Validate** — walidacja twarda i miękka.
7. **Score** — wyliczenie quality score i rekomendowanego outcome.
8. **Outcome** — mapowanie na `TaskStatus` i `FinalOutcome`.
9. **Persist + Telemetry** — hooki rozszerzalne.

## Scenariusze błędów

- Timeout inferencji => wynik `failed` z metadanymi błędu.
- Provider exception po wszystkich retry => `failed`.
- Soft warnings + `abstain_allowed=true` => `abstained`.
