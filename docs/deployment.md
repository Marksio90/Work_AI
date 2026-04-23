# Deployment

## Docker Compose (lokalnie i preprod)

1. Uzupełnij `.env` na bazie `.env.example`.
2. Uruchom:

```bash
docker compose -f infra/compose/docker-compose.yml up --build
```

## Minimalny stack

- API container
- Worker container
- Redis
- (opcjonalnie) Postgres

## Checklist

- migracje DB uruchomione (Alembic),
- healthcheck providera aktywny,
- monitorowane metryki jakości i latency,
- alerty na wzrost `abstain` i `failed`.
