# Development

## Lokalne uruchomienie

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## Offline evaluation

```bash
python scripts/offline_eval.py \
  --fixtures-dir tests/fixtures/tasks \
  --report-path artifacts/offline-eval-report.json
```

Raport zawiera:

- `quality_avg`
- `latency_avg_ms`
- `valid_output_rate`

## Rozszerzanie systemu

- **Task**: dodaj nowy `TaskType`, schemat i constraints.
- **Provider**: zaimplementuj `BaseLLMProvider` i zarejestruj w `providers/factory.py`.
- **Validator**: dodaj walidator i podłącz do `CompositeValidator`.
- **Adapter**: dodaj integrację w `packages/bt_adapter`.
