# Scoring i progi decyzji

`QualityEngine` liczy końcową jakość odpowiedzi deterministycznie i transparentnie.

## Składowe wzoru

Wszystkie metryki są w zakresie `[0.0, 1.0]`.

- `structural_validity_score` — jakość strukturalna po walidacji (schema/constraints/consistency).
- `semantic_validity_score` — zgodność semantyczna odpowiedzi z celem zadania.
- `completeness_score` — proporcja pól oczekiwanych do faktycznie wypełnionych.
- `confidence_score` — pewność modelu/toru inferencyjnego.
- `latency_penalty` — kara za wolną odpowiedź.
- `repair_penalty` — kara za konieczność napraw po inferencji.

### Wzór

```text
base_score =
  0.30 * structural_validity_score +
  0.25 * semantic_validity_score +
  0.20 * completeness_score +
  0.25 * confidence_score

final_score = clamp(base_score - latency_penalty - repair_penalty, 0.0, 1.0)
```

## Dokładne kary

### `latency_penalty`

- `0.00` dla `latency_ms <= 1500`
- `0.05` dla `1500 < latency_ms <= 4000`
- `0.10` dla `4000 < latency_ms <= 8000`
- `0.20` dla `latency_ms > 8000`

### `repair_penalty`

- `0.00` gdy brak napraw
- `0.08 * repair_count`, maksymalnie `0.30`

## Dokładne progi success/abstain/error

Decyzja jest wyznaczana na podstawie `final_score`:

- **success**: `final_score >= 0.80`
- **abstain**: `0.55 <= final_score < 0.80`
- **error**: `final_score < 0.55`

Te progi są używane do `recommended_outcome` w szczegółach scoringu.
