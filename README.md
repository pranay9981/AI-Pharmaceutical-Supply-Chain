# Pharmaceutical Supply Chain Control Tower

**Synthetic data for demonstration only. Not for operational decision making.**

The control tower will help a planner see which markets could run short after an active pharmaceutical ingredient (API) delivery slips, trace the impact to supply records, and compare responses for human review.

## Run the Week 2 sample

Run these commands from the repository root with Python 3.11 or later and SQLite 3.38 or later as bundled with Python.

```powershell
python -m control_tower init-db --sample --database data/output/week_02_sample.sqlite3
python -m control_tower trace --database data/output/week_02_sample.sqlite3 --shipment DEMO-SHIP-MKT
```

The first command creates the local sample database and refuses to overwrite an existing file. If the sample already exists, run the trace command directly. Omit `--sample` for an empty schema. The trace reads the market shipment’s linked batch, production, material requirements, and purchase orders. The expanded generator, projections, and trained forecasts are scheduled for Weeks 3–5.

Run the schema and sample checks with `python -B -m unittest discover -s tests -v`.

## Project references

- [Week 1 scope, architecture, glossary, and acceptance checks](docs/week_01_foundation.md)
- [Week 2 entity relationships, data dictionary, and scenario catalogue](docs/week_02_data_model.md)
- [Hand-calculated API-delay benchmark](examples/api_delay_benchmark.json)
- [12-week schedule and daily tasks](AI_Supply_Chain_Control_Tower_12_Week_Executive_Schedule.xlsx)
- Company brief (local reference)

The operational sandbox for this rebuild will use a new SQLite database under `data/output/`. The earlier implementation and dataset are available on `main`.
