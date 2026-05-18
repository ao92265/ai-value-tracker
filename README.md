# ai-value-tracker

Measures Claude Code AI spend against the customer value it produces. Answers the question "is the AI investment paying back?" with numbers, per feature, per week.

## Why

Most teams can describe AI ROI as a story. This tool turns it into a chart. Spend in. Value out. Ratio over time.

## What it does

| Module | Job |
|---|---|
| `avt.spend` | Walk Claude Code JSONL logs, sum token cost per session, attribute to branch and GitHub issue. |
| `avt.value` | Pull GitHub PRs by issue. Lines changed, files touched, merge state, age. |
| `avt.report` | Join spend and value. Per-issue cost-vs-value CSV plus a bar chart. |
| `avt.telemetry` | Wraith product-side spec. Schema for AI-accepted vs human-edited events. |

## Install

```bash
cd ~/Repos/ai-value-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Use

```bash
avt-spend --days 30 --out spend.csv
avt-value --days 30 --out value.csv
avt-report --spend spend.csv --value value.csv --out report.csv --chart chart.png
```

Or run the weekly cron:

```bash
~/Repos/ai-value-tracker/bin/avt-weekly
```

## Pricing

Token prices live in `src/avt/spend.py` near the top. Update when Anthropic changes them.

## Output

`report.csv` columns: `issue, branch, cost_usd, prs_open, prs_merged, lines_added, lines_removed, files_changed, value_score, ratio`.

`value_score` is a placeholder formula. Replace with the real customer-recognised measure once product telemetry is wired up (see `docs/wraith-telemetry-spec.md`).

## Limits

Pricing is approximate. Pre-launch.

Branch attribution uses git reflog timestamps near the session start. Sessions started before a checkout get attributed to the previous branch. About 5 percent noise.

`value_score` is a stand-in until product telemetry lands.

## License

MIT.
