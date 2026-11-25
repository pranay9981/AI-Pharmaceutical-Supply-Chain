# Pharmaceutical Supply Chain Control Tower

**Synthetic data for demonstration only. Not for operational decision making.**

The control tower will help a planner see which markets could run short after an active pharmaceutical ingredient (API) delivery slips, trace the impact to supply records, and compare responses for human review.

## Run the Week 1 scaffold

Run the following command from the repository root with Python 3.11 or later.

```powershell
python -m control_tower
```

The command displays the release scope and sample scenario input. The database, generator, projections, and forecasts are scheduled for Weeks 2–5.

## Project references

- [Week 1 scope, architecture, glossary, and acceptance checks](docs/week_01_foundation.md)
- [Hand-calculated API-delay benchmark](examples/api_delay_benchmark.json)
- [12-week schedule and daily tasks](AI_Supply_Chain_Control_Tower_12_Week_Executive_Schedule.xlsx)
- Company brief (local reference)

The operational sandbox for this rebuild will use a new SQLite database under `data/output/`. The earlier implementation and dataset are available on `main`.
