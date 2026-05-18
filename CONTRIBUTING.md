# Contributing

## Dev setup

```bash
git clone https://github.com/ao92265/ai-value-tracker
cd ai-value-tracker
make install
source .venv/bin/activate
```

## Run the suite

```bash
avt-spend --days 7 --out out/spend.csv
avt-value --days 7 --out out/value.csv
avt-report --spend out/spend.csv --value out/value.csv --out out/report.csv --chart out/chart.png
```

## Adding pricing

`src/avt/spend.py` has a `PRICES` dict keyed by model prefix. Anthropic publishes prices per million tokens. Add the model, push a PR.

## Adding a value source

Right now value comes from GitHub PRs (`avt.value`) and a stub product reader (`avt.telemetry`). New sources:

1. Add a module under `src/avt/`.
2. Output a CSV keyed on `issue`.
3. Update `avt.report` to merge it in.

## Tests

Not yet. Contributions welcome.

## Code style

Plain Python 3.11. No type checker. No linter set up. Keep it boring.
