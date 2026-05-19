# ai-value-tracker

![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![status](https://img.shields.io/badge/status-alpha-orange)

Measures Claude Code AI spend against the customer value it produces. Answers the question "is the AI investment paying back?" with numbers, per feature, per week. Drops a CSV and a bar chart in your inbox every Monday.

Built because asking "how much are we spending on Claude?" gets a number, asking "what did it produce?" gets a story. This turns the story into a number.

## What you get

A single command that walks your Claude Code session logs, joins them to the GitHub issues they belong to, pulls the PR stats those issues produced, and emits one CSV row per issue with cost and value side by side.

```
issue   branch                       sessions  cost_usd  prs_merged  lines_added  value_score  ratio
#7922   feat/issue-7922-foo                45   3944.42           2          634         1261   0.32
#6830   feat/issue-6830-bar                12   1015.53           1          313          581   0.57
```

Plus a bar chart of the top N issues by spend, with value scored alongside.

## Why bother

Three reasons.

**Cost without attribution is unmanageable.** "Last month was $27k" is a panic number. "Issue #7922 was $3.9k, shipped 2 PRs, 634 lines" is a decision.

**Fast feedback on routing.** If sonnet sessions are producing the same ratio as opus sessions on the same kind of work, route more work to sonnet.

**Commercial conversation starter.** Once product-side telemetry is wired (see `docs/wraith-telemetry-spec.md`), `value_score` becomes "minutes of reviewer time saved" or "drafts accepted." That's the number for pricing conversations.

## Cost sources

AI spend lives in more places than just Claude Code. `avt-cost` unifies them.

| Source | Adapter | Status |
|---|---|---|
| Claude Code (JSONL logs) | `--claude` | shipped |
| Anthropic API (console CSV export) | `--anthropic-csv <path>` | shipped |
| GitHub Copilot (admin API per seat) | `--copilot-org <org>` | shipped |
| Generic vendor (any CSV: Intercom Fin, Gong, Cursor, OpenAI, etc.) | `--vendor-csv <path> --vendor-source <name>` | shipped |
| Azure billing AI resource group | `--azure-billing` | planned |
| OpenAI usage API | `--openai` | planned |

Run any combination in one shot:

```bash
avt-cost --claude --days 30 \
         --anthropic-csv anthropic-export.csv \
         --copilot-org harriscomputer \
         --vendor-csv gong-bill.csv --vendor-source gong \
         --out out/cost.csv
```

Output is one unified CSV with a `source` column, plus a percentage breakdown by source on stderr.

## How it works

```
~/.claude/projects/<project>/*.jsonl   →  avt-spend  →  spend.csv
                                                          ↓
GitHub repo (gh CLI)                   →  avt-value  →  value.csv
                                                          ↓
                                          avt-report → report.csv + chart.png
```

Spend side reads Claude Code's per-session JSONL logs, sums token usage per session, multiplies by approximate model pricing, and attributes the session to a branch via git reflog timestamp matching. Branch then maps to an issue number (from branch name or commit `#NNNN` references).

Value side reads the GitHub repo via `gh`, pulls every PR that references each issue, and sums lines changed, files touched, PR merge state.

Report side joins on issue number, computes a placeholder `value_score = lines + (merged_prs × 200)`, and writes CSV + bar chart.

The placeholder formula is deliberately simple. Replace it with the real customer-recognised measure once you have product telemetry.

## Install

```bash
git clone https://github.com/ao92265/ai-value-tracker
cd ai-value-tracker
make install
```

Requires Python 3.11+, `gh` CLI authenticated, and a Claude Code project directory with JSONL logs.

## Use

One-shot for the last 30 days:

```bash
source .venv/bin/activate
avt-spend  --days 30 --out out/spend.csv
avt-value  --days 30 --out out/value.csv  --repo i2group-FIS/Wraith
avt-report --spend out/spend.csv --value out/value.csv \
           --out out/report.csv --chart out/chart.png --top 20
```

Or just:

```bash
make report
```

Or weekly cron (snapshots to `~/.claude/observatory-logs/avt/YYYY-MM-DD/`):

```bash
0 9 * * 1  /Users/you/Repos/ai-value-tracker/bin/avt-weekly >> /tmp/avt-weekly.log 2>&1
```

## Configure

**Project directory.** `avt-spend --project /Users/you/.claude/projects/-your-project-here`. Default is hard-coded to Wraith. Change it in `src/avt/spend.py:DEFAULT_PROJECT` or pass `--project` every time.

**Repo.** `avt-value --repo owner/repo`. Default `i2group-FIS/Wraith`. Override per call.

**Pricing.** `src/avt/spend.py` top of file. USD per million tokens, per model. Update when Anthropic changes prices.

**Value formula.** `src/avt/report.py:value_score()`. Default is a code-volume proxy. Swap it for whatever you actually care about.

## Output

`report.csv`:

| Column | Meaning |
|---|---|
| `issue` | GitHub issue number, or `(unattributed)` |
| `branch` | First branch seen for this issue |
| `sessions` | Claude Code sessions in window |
| `cost_usd` | Sum of all session costs |
| `prs_open` / `prs_merged` / `prs_closed` | PR counts referencing this issue |
| `lines_added` / `lines_removed` / `files_changed` | Sum across PRs |
| `value_score` | Placeholder. Replace. |
| `ratio` | `value_score / cost_usd` |

`chart.png`: dual-axis bar chart, top N issues by spend, cost (red) and value (green) side by side.

## Product telemetry

The CSV is half the story. Lines of code is not value. The other half is product-side telemetry: when a user accepts an AI-drafted field, edits it, or rejects it. That signal is what should drive `value_score`.

Spec is in [`docs/wraith-telemetry-spec.md`](docs/wraith-telemetry-spec.md). Prisma schema, endpoint, permission, rollout. Once it ships, `avt.telemetry` reads from it and replaces the placeholder.

## FAQ

### Can't I just look at the Claude Code dashboard?

For a single tool, single user, yes. `claude /cost`, the native dashboard, and `~/Repos/claude-observatory` cover that.

This tool adds four things native doesn't:

1. **Per-issue attribution.** Native says "Tuesday cost $200." This says "Issue #7922 cost $3.9k across the week, attributed via branch + git reflog."
2. **Cross-vendor unification.** Claude dashboard + Copilot UI + Anthropic console + Cursor portal + vendor invoice = 5 places. This puts them in one CSV with a `source` column.
3. **Cost-vs-value join.** Native shows cost. Doesn't pull GitHub PRs against the spend window and compute a ratio.
4. **Per-tenant value attribution.** Once product telemetry lands, native can't tell you "Jersey tenant generated $X of AI value." This will.

If your use case is "I want to see my Claude bill", use `claude /cost`. If it's "the CFO is asking where the AI money went and what it produced", use this.

### What if we're on a flat subscription, not the API?

Read carefully — this is the most common misuse.

If your team is on Claude Max ($200/mo flat), Claude Pro, or Copilot Business ($19/seat), the per-token numbers this tool prints are **hypothetical**. They are "what this would cost on the API at list price." Actual cash is the subscription.

Run with the right mode:

```bash
avt-cost --claude --cost-mode subscription --sub-cash 200
```

Output then includes a banner plus a ratio:

```
HYPOTHETICAL COST MODE (subscription plan in use)
Numbers below are token-equivalent API cost, not cash.

Total: $4682.99 across 55 rows

Hypothetical API-equivalent: $4682.99
Real subscription cash:      $200.00
Ratio (hypothetical/cash):   23.41x
```

The hypothetical number is still useful for:

- **Routing.** "This task burned $80 of opus-equivalent and could've been $12 of sonnet-equivalent" is actionable even if you paid neither in cash.
- **Capacity planning.** Flat sub doesn't mean infinite throughput. Token-equivalent flags when you'll hit throttling.
- **Per-feature comparison.** Ratio between features is meaningful even when absolute is hypothetical.
- **Sub-vs-API decision.** A 23x ratio says "stay on the sub." A 0.4x ratio says "switch to API."

Use `--cost-mode api` (default) only when you actually pay per token.

### When does this tool earn its keep?

| Scenario | Native enough? | Use this? |
|---|---|---|
| Solo dev curious about session cost | yes | overkill |
| BU with mixed Max/API users | partial | useful for attribution |
| BU pitching outcome pricing to a customer | no | needed (value side) |
| Multi-BU report to leadership | no (5 dashboards) | needed (unification) |
| Finance asking "did we save the $1M we promised?" | no | needed (cost-vs-value) |
| Quarterly per-tenant pricing review | no | needed (telemetry) |

### Is the value side useful before product telemetry lands?

Partially. Today `value_score = lines + (merged_prs × 200)`. That's a code-volume proxy. Acceptable as a relative measure between features. Not acceptable as an absolute "did AI pay back" number.

For the absolute number, ship the product telemetry described in `docs/wraith-telemetry-spec.md`. Until then, treat the ratio as directional, not financial.

### Why not Azure DevOps / GitLab / Jira out of the box?

`avt-value` is the only GitHub-specific module today. Spend side runs on any project. Other VCS adapters are ~100 lines each. PRs welcome (see `CONTRIBUTING.md`).

### What about pricing accuracy?

Token prices in `src/avt/spend.py` are list-price as of late 2025. They will drift. Update the dict when Anthropic publishes new prices. Enterprise volume discounts are not modelled — apply a flat multiplier downstream if needed.

### What this is NOT

- Not a billing system. Talks to vendor invoices, doesn't replace them.
- Not an observability tool. Use `~/Repos/claude-observatory` for hook-level / waste analysis.
- Not a real-time dashboard. Daily/weekly batch.
- Not a finance system of record. Numbers in hypothetical mode are not auditable.

## What it doesn't do yet

- Pricing is approximate. Pre-launch model variants might be off.
- Branch attribution uses git reflog timestamps near the session start. Sessions started before a checkout get attributed to the previous branch. About 5 percent noise.
- `value_score` is a stand-in. The real number comes from product telemetry.
- No tests. v0.1.
- No web UI. CSV plus PNG.

## Layout

```
ai-value-tracker/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── Makefile
├── pyproject.toml
├── bin/avt-weekly             cron-friendly snapshot
├── src/avt/
│   ├── spend.py               JSONL → cost per session, branch, issue
│   ├── value.py               gh → PRs, lines, files per issue
│   ├── report.py              join + CSV + chart
│   └── telemetry.py           product-side stub
├── docs/
│   └── wraith-telemetry-spec.md
└── examples/weekly-cron.sh
```

## License

MIT.
