# Deployment

## Docker Compose (lokalnie i preprod)

1. (Opcjonalnie) skopiuj `.env.example` do `.env` i nadpisz ustawienia.
2. Uruchom pełny stack:

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

Compose uruchamia:

- Postgres,
- Redis,
- kontener `migrate` (Alembic `upgrade head`),
- API,
- worker Celery,
- beat Celery (polling zewnętrznych płatnych tasków).

API i worker startują dopiero po poprawnym zakończeniu migracji oraz po healthcheckach Redis/Postgres.

## Minimalny stack

- API container
- Worker container
- Redis
- Postgres

## Checklist

- migracje DB uruchomione (Alembic),
- healthcheck providera aktywny,
- monitorowane metryki jakości i latency,
- alerty na wzrost `abstain` i `failed`.


## Tryb RapidAPI

Ustaw `TASK_SOURCE_MODE=rapidapi_inbound` oraz `RAPIDAPI_PROXY_SECRET`.
W tym trybie endpoint `POST /v1/tasks` weryfikuje nagłówek `X-RapidAPI-Proxy-Secret`,
a ekonomia oparta jest o eventy requestów zamiast pull-ingu task source.
