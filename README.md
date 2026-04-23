# Work_AI

Work_AI to modularny system orkiestracji tasków AI: przyjmuje kontrakty zadań, uruchamia inference przez provider, waliduje output, liczy score jakości i zwraca deterministyczny wynik.

## Funkcjonalności

- Pipeline tasków: `accept -> preprocess -> strategy -> inference -> repair -> validate -> score -> outcome`.
- Retry i timeout na inferencji wg `ExecutionPolicy`.
- Walidacja wieloetapowa (schema + constraints + consistency).
- Deterministyczny scoring (`quality`, `latency`, `valid-output-rate`).
- Idempotency + dedup cache (Redis).
- Fixture-based offline evaluation harness.

## Struktura repo

- `apps/api` — FastAPI endpoints.
- `apps/worker` — entrypoint workera Celery.
- `packages/*` — kontrakty, orchestrator, providerzy, walidacja, scoring, cache.
- `tests/unit`, `tests/integration`, `tests/e2e`, `tests/fixtures/tasks`.
- `scripts/offline_eval.py` — offline harness z raportem.
- `docs/*.md` — architektura, flow, scoring, walidacja, development, deployment.

## Wymagania

- Python 3.11+
- (opcjonalnie) Docker + Docker Compose

## Uruchomienie lokalne

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
pytest
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

API health:

```bash
curl http://localhost:8000/v1/health
```

## Docker Compose

Cały stack (API, worker, Redis, Postgres, migracje Alembic) uruchamiany jest przez Dockera:

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

Serwisy:

- API: `http://localhost:8000`
- Redis: `localhost:6379`
- Postgres: `localhost:5432`
- Worker Celery (background)
- Beat Celery (cykliczny polling płatnych tasków ze źródła)
- `migrate` (jednorazowy kontener uruchamiający `alembic upgrade head`)

Jeśli chcesz nadpisać wartości domyślne, skopiuj `.env.example` do `.env` i zmień zmienne środowiskowe.

## Testy

```bash
pytest tests/unit
pytest tests/integration
pytest tests/e2e
```

Zakres pokrycia testów:

- walidatory,
- scoring,
- retry/timeout,
- abstain,
- idempotency i cache,
- provider error paths,
- harness offline evaluation.

## Fixtures tasków

Przykładowe kontrakty w `tests/fixtures/tasks`:

- `success_extraction.json`
- `abstain_generation.json`
- `provider_error.json`

## Offline evaluation harness

Uruchomienie:

```bash
python scripts/offline_eval.py \
  --fixtures-dir tests/fixtures/tasks \
  --report-path artifacts/offline-eval-report.json
```

Wynik raportu JSON zawiera:

- `quality_avg`
- `latency_avg_ms`
- `valid_output_rate`
- tabelę per-task (`rows`)

## Jak rozszerzyć system

### 1) Nowy task

1. Dodaj/wybierz `TaskType`.
2. Zdefiniuj `output_schema` i `constraints`.
3. Dodaj fixture + testy integration/e2e.

### 2) Nowy provider

1. Utwórz klasę dziedziczącą po `BaseLLMProvider`.
2. Implementuj `generate_text`, `generate_structured`, `healthcheck`, `model_info`.
3. Zarejestruj provider w `packages/providers/factory.py`.
4. Dodaj testy ścieżek błędów i timeoutów.

### 3) Nowy validator

1. Utwórz validator oparty o `BaseValidator`.
2. Dodaj reguły do `validate(contract, output_payload)`.
3. Podłącz go w `CompositeValidator`.
4. Dodaj testy unit + integration.

### 4) Nowy adapter

1. Rozszerz `packages/bt_adapter` o integrację kanału wejścia/wyjścia.
2. Dodaj mapowanie do `TaskContract` i `TaskResult`.
3. Zweryfikuj przepływ e2e i offline eval.

## Dokumentacja

- `docs/architecture.md`
- `docs/execution-flow.md`
- `docs/scoring.md`
- `docs/validation.md`
- `docs/development.md`
- `docs/deployment.md`


## Monetyzacja / source tasks

System zawiera connector źródła zadań (`packages/task_source`) i prosty silnik opłacalności (`packages/economics`).

- Cykliczny polling realizuje Celery Beat (`ingest_source_tasks`).
- API endpoint `POST /v1/source/pull` pozwala ręcznie wymusić pobranie tasków.
- API endpoint `GET /v1/economics/summary` zwraca agregaty przychodu/kosztu/marży.
