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
- worker Celery.

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
