# Device and app adapters

The project is not Apple Watch specialized. Apple Health is the first native health-export parser
because it offers a user-controlled XML export; every engine consumes the device-independent schema.

| Source | Current path | Native? | Reconciliation boundary |
|---|---|---:|---|
| Apple Health | XML or ZIP | Yes | Additive metrics are totaled per source, then the largest source-day total is selected to reduce phone/watch overlap. |
| Hevy | CSV | Yes | Working, warm-up, drop, and failure sets remain labelled. |
| Strong | CSV | Yes | Weight-like generic `Weight` is interpreted as pounds for this known export. |
| Garmin | Exported or manually normalized CSV | Schema-compatible | The user must verify whether daily totals already combine devices. |
| Fitbit | Exported or manually normalized CSV | Schema-compatible | The user must verify timezone and daily aggregation. |
| COROS | Exported or manually normalized CSV | Schema-compatible | Training and daily-health exports may require separate normalization. |
| Scale, food logger, spreadsheet | Generic CSV | Yes | Duplicate dates use metric-specific sum, mean, or median rules. |

“Schema-compatible” is not a claim of a tested vendor API integration. It means the export can be
mapped to the generic columns below without changing analytical code.

## Daily CSV contract

Required: `date` plus at least one recognized metric. Recognized canonical fields are:

```text
weight_kg, energy_intake_kcal, active_energy_kcal, steps, sleep_hours,
training_minutes, resting_hr_bpm, hrv_ms
```

Aliases include `weight_lb`, `calories`, `step_count`, `sleep`, `workout_minutes`, `rhr`, and `hrv`.
Repeated dates are handled as follows:

- body weight: median;
- intake, active energy, steps, training minutes: sum;
- sleep, resting heart rate, HRV: mean.

If an upstream export repeats a daily total on every row, normalize it before import; summing those
rows would be incorrect.

## Strength CSV contract

Required: date, exercise, reps, and either kg or pound weight. Optional: RPE, set type, body weight,
and duration. Generic ambiguous `weight` is treated as pounds because it is a Strong alias; custom
exports should use `weight_kg` or `weight_lb` explicitly.

## Adapter acceptance checklist

- Include a small synthetic fixture, never a real user export.
- Test timezone/date parsing and all supported units.
- State whether values are event-level, interval-level, or already-daily totals.
- Test duplicates from two devices.
- Add a quality flag whenever reconciliation discards or combines values.
