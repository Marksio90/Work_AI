# Scoring i progi decyzji

`QualityEngine` liczy końcową jakość odpowiedzi deterministycznie i transparentnie.

## Składowe wzoru

Wszystkie metryki są w zakresie `[0.0, 1.0]`.

- `structural_validity_score` — jakość strukturalna po walidacji.
- `semantic_validity_score` — zgodność semantyczna odpowiedzi z celem zadania.
- `completeness_score` — proporcja pól oczekiwanych do faktycznie wypełnionych.
- `confidence_score` — pewność toru inferencyjnego.
- `latency_penalty` — kara za wolną odpowiedź.
- `repair_penalty` — kara za konieczność napraw.

### Wzór

```text
base_score =
  0.30 * structural_validity_score +
  0.25 * semantic_validity_score +
  0.20 * completeness_score +
  0.25 * confidence_score

final_score = clamp(base_score - latency_penalty - repair_penalty, 0.0, 1.0)
```

## Kary i progi

- latency: `0.00 / 0.05 / 0.10 / 0.20` dla progów `<=1500 / <=4000 / <=8000 / >8000 ms`.
- repair: `0.08 * repair_count` (max `0.30`).

Outcome recommendation:

- **success**: `final_score >= 0.80`
- **abstain**: `0.55 <= final_score < 0.80`
- **error**: `final_score < 0.55`
