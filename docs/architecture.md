# Architektura Work_AI

## Komponenty

- **API (`apps/api`)**: punkt wejścia HTTP i walidacja kontraktu wejściowego.
- **Worker (`apps/worker`)**: asynchroniczne wykonanie tasków.
- **Orchestrator (`packages/orchestrator`)**: pipeline `accept -> inference -> repair -> validate -> score -> outcome`.
- **Providers (`packages/providers`)**: adaptery modeli (mock, Ollama, przyszłe integracje).
- **Validators (`packages/validators`)**: schema/constraints/consistency.
- **Scoring (`packages/scoring`)**: deterministyczna ocena jakości.
- **Cache (`packages/cache`)**: idempotency i deduplication.
- **Queue (`packages/queue`)**: integracja z Celery + polling task source.
- **Task Source (`packages/task_source`)**: konektory do platform z płatnymi taskami.
- **Economics (`packages/economics`)**: decyzje opłacalności i metryki marży.
- **Persistence (`packages/persistence`)**: modele i sesje bazy.

## Zasady projektowe

1. Deterministyczne modele danych (`TaskContract`, `TaskResult`) z fingerprintami.
2. Jawny `ExecutionPolicy` (retry, timeout, abstain).
3. Separacja odpowiedzialności: provider ≠ validator ≠ scoring.
4. Testability-by-design: mock provider i fixture-based eval harness.

- Tryb `rapidapi_inbound` rozlicza usage per request i waliduje `X-RapidAPI-Proxy-Secret`.
