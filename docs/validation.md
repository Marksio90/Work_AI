# Walidacja

## Walidatory

- `SchemaValidator`: wymagane pola, typy, `additionalProperties`.
- `ConstraintValidator`: twarde reguły (`required_non_empty`, zakresy liczbowe, długości, forbidden values).
- `ConsistencyValidator`: miękkie reguły jakości (`quality_required_fields`, `mutually_exclusive`).

## Composite decision

- Hard issue => `validation_error`.
- Tylko soft issues + `abstain_allowed=true` => `abstain`.
- Tylko soft issues + `abstain_allowed=false` => `validation_error`.
- Brak issues => `pass`.
