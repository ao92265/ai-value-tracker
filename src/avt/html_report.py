"""Render a single-page HTML cost-and-value report.

Inputs:
    --cost    avt-cost CSV  (source, started, cost_usd, attributed_to, units, notes)
    --report  avt-report CSV (optional: issue, branch, cost_usd, prs_*, value_score, ratio)

Output:
    --out     single self-contained HTML file (inline CSS + SVG, no JS)
"""

import argparse
import csv
import html
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone


PALETTE = {
    "blue":   "#1d4ed8",
    "teal":   "#0d9488",
    "amber":  "#b45309",
    "purple": "#6d28d9",
    "gray":   "#94a3b8",
    "red":    "#dc2626",
    "green":  "#16a34a",
}


CSS = """
:root {
  --bg: #ffffff; --bg-soft: #f8fafc; --bg-deep: #f1f5f9;
  --ink: #0f172a; --mute: #64748b; --border: #e2e8f0;
  --accent: #1d4ed8; --accent-soft: #dbeafe;
  --teal: #0d9488; --amber: #b45309; --purple: #6d28d9;
  --red: #dc2626; --green: #16a34a;
  --topbar: #312e81; --topbar-soft: #c7d2fe;
  --radius: 8px; --radius-md: 12px;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  color: var(--ink); background: var(--bg-soft); line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
.topbar { background: var(--topbar); color: #fff; padding: 16px 32px;
          display: flex; align-items: center; gap: 22px; }
.topbar .brand { font-family: 'JetBrains Mono', monospace; font-weight: 600;
                 font-size: 14px; letter-spacing: -0.02em; }
.topbar .dim { color: var(--topbar-soft); }
.topbar .spacer { flex: 1; }
.topbar .generated { font-family: 'JetBrains Mono', monospace; font-size: 11.5px;
                     color: var(--topbar-soft); }
.wrap { max-width: 1100px; margin: 0 auto; padding: 36px 32px 64px; }
h1 { font-size: 30px; font-weight: 700; letter-spacing: -0.025em; margin: 0 0 6px; }
.subtitle { color: var(--mute); margin: 0 0 28px; font-size: 15px; }
.subtitle strong { color: var(--ink); font-weight: 600; }
.kicker { font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
          text-transform: uppercase; letter-spacing: 0.08em; color: var(--mute);
          margin-bottom: 6px; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
        margin-bottom: 28px; }
@media (max-width: 800px) { .kpis { grid-template-columns: repeat(2, 1fr); } }
.kpi { background: #fff; border: 1px solid var(--border);
       border-radius: var(--radius-md); padding: 16px 18px 14px; }
.kpi .label { font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
              text-transform: uppercase; letter-spacing: 0.08em; color: var(--mute);
              margin-bottom: 6px; }
.kpi .value { font-size: 26px; font-weight: 700; letter-spacing: -0.025em; line-height: 1.05; }
.kpi .note { font-size: 12px; color: var(--mute); margin-top: 4px; }
.kpi.accent { border-top: 3px solid var(--accent); }
.kpi.teal   { border-top: 3px solid var(--teal); }
.kpi.amber  { border-top: 3px solid var(--amber); }
.kpi.purple { border-top: 3px solid var(--purple); }
.panel { background: #fff; border: 1px solid var(--border);
         border-radius: var(--radius-md); padding: 20px 22px 22px; margin-bottom: 18px; }
.panel h2 { font-size: 15px; font-weight: 700; margin: 0 0 4px; letter-spacing: -0.01em; }
.panel .panel-sub { color: var(--mute); font-size: 12.5px; margin: 0 0 16px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
.grid-2 .panel { margin-bottom: 0; }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
thead th { text-align: left; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;
           font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;
           color: var(--mute); padding: 6px 6px 10px; border-bottom: 1px solid var(--border); }
tbody td { padding: 8px 6px; border-bottom: 1px solid var(--border); vertical-align: middle; }
tbody tr:last-child td { border-bottom: 0; }
td.num { font-family: 'JetBrains Mono', monospace; text-align: right; font-size: 12.5px; }
td.key { font-family: 'JetBrains Mono', monospace; font-size: 12.5px; }
code { background: var(--bg-deep); padding: 1px 6px; border-radius: 4px;
       font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.plan-banner { background: #fef3c7; border-left: 4px solid var(--amber);
               border-radius: 0 var(--radius) var(--radius) 0; padding: 14px 22px;
               margin: 0 0 18px; font-size: 13.5px; line-height: 1.55; color: var(--ink); }
.plan-banner .label { display: inline-block; font-family: 'JetBrains Mono', monospace;
                      font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.08em;
                      color: var(--amber); font-weight: 600; margin-right: 8px; }
.plan-banner strong { font-weight: 600; }
.plan-banner .mono { font-family: 'JetBrains Mono', monospace; background: rgba(255,255,255,0.6);
                     padding: 1px 6px; border-radius: 4px; font-size: 12.5px; }
.footer { margin-top: 24px; padding-top: 18px; border-top: 1px dashed var(--border);
          font-size: 12.5px; color: var(--mute); line-height: 1.6; }
.legend { display: flex; flex-wrap: wrap; gap: 18px; margin-top: 14px; font-size: 12.5px; }
.legend .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px;
                  margin-right: 6px; vertical-align: middle; }
"""


def fmt_money(n):
    return f"${n:,.2f}"


def fmt_int(n):
    return f"{n:,}"


def fmt_compact(n):
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def read_csv(path):
    if not path or not os.path.isfile(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def daily_totals(rows):
    by_day = defaultdict(float)
    for r in rows:
        started = r.get("started", "")[:10]
        if not started:
            continue
        try:
            cost = float(r.get("cost_usd", 0) or 0)
        except ValueError:
            continue
        by_day[started] += cost
    return sorted(by_day.items())


def source_totals(rows):
    by_src = defaultdict(float)
    for r in rows:
        try:
            cost = float(r.get("cost_usd", 0) or 0)
        except ValueError:
            cost = 0
        by_src[r.get("source", "unknown")] += cost
    return sorted(by_src.items(), key=lambda x: x[1], reverse=True)


def issue_totals(rows):
    by_issue = defaultdict(lambda: {"cost": 0.0, "sessions": 0})
    for r in rows:
        attr = r.get("attributed_to", "")
        if not attr.startswith("issue:"):
            continue
        key = attr[len("issue:"):]
        try:
            cost = float(r.get("cost_usd", 0) or 0)
        except ValueError:
            cost = 0
        by_issue[key]["cost"] += cost
        by_issue[key]["sessions"] += 1
    return sorted(by_issue.items(), key=lambda x: x[1]["cost"], reverse=True)


def bar_svg(items, width=880, height=260, color="#1d4ed8"):
    if not items:
        return "<svg></svg>"
    pad_l, pad_r, pad_t, pad_b = 56, 18, 16, 44
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    max_val = max(v for _, v in items) or 1
    step = 4
    grid = "".join(
        f'<line x1="{pad_l}" y1="{pad_t + plot_h * (1 - i/step):.1f}" '
        f'x2="{width-pad_r}" y2="{pad_t + plot_h * (1 - i/step):.1f}" '
        f'stroke="#e2e8f0" stroke-width="1"/>'
        for i in range(step + 1)
    )
    n = len(items)
    bar_w = plot_w / max(n, 1) * 0.72
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" preserveAspectRatio="xMidYMid meet" style="display:block;">', grid]
    for i, (label, val) in enumerate(items):
        cx = pad_l + (i + 0.5) * plot_w / n
        bh = (val / max_val) * plot_h
        y = pad_t + plot_h - bh
        out.append(
            f'<rect x="{cx - bar_w/2:.1f}" y="{y:.1f}" '
            f'width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" rx="3" ry="3">'
            f'<title>{html.escape(label)}: {fmt_money(val)}</title></rect>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="{y - 6:.1f}" text-anchor="middle" '
            f'font-family="JetBrains Mono, monospace" font-size="10.5" fill="#0f172a" '
            f'font-weight="600">{fmt_money(val) if val < 1000 else f"${val/1000:.1f}k"}</text>'
        )
        out.append(
            f'<text x="{cx:.1f}" y="{height - 14:.1f}" text-anchor="middle" '
            f'font-family="JetBrains Mono, monospace" font-size="11" fill="#94a3b8">'
            f'{html.escape(label[-5:])}</text>'
        )
    for i in range(step + 1):
        y_pos = pad_t + plot_h * (1 - i/step) + 4
        v = max_val * i / step
        out.append(
            f'<text x="{pad_l - 8:.1f}" y="{y_pos:.1f}" text-anchor="end" '
            f'font-family="JetBrains Mono, monospace" font-size="11" fill="#94a3b8">'
            f'${v/1000:.1f}k</text>'
        )
    out.append("</svg>")
    return "".join(out)


def stacked_svg(items, width=880, height=36):
    total = sum(v for _, v in items) or 1
    x = 0
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" preserveAspectRatio="none" style="display:block;border-radius:6px;overflow:hidden;">']
    colors = [PALETTE["blue"], PALETTE["purple"], PALETTE["amber"], PALETTE["teal"], PALETTE["gray"], PALETTE["red"], PALETTE["green"]]
    for i, (label, val) in enumerate(items):
        w = (val / total) * width
        color = colors[i % len(colors)]
        out.append(
            f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="{height}" fill="{color}">'
            f'<title>{html.escape(label)}: {fmt_money(val)} ({val/total*100:.1f}%)</title></rect>'
        )
        x += w
    out.append("</svg>")
    return "".join(out)


def legend(items):
    total = sum(v for _, v in items) or 1
    colors = [PALETTE["blue"], PALETTE["purple"], PALETTE["amber"], PALETTE["teal"], PALETTE["gray"], PALETTE["red"], PALETTE["green"]]
    parts = []
    for i, (label, val) in enumerate(items):
        color = colors[i % len(colors)]
        parts.append(
            f'<span><span class="swatch" style="background:{color}"></span>'
            f'<span style="font-weight:500;">{html.escape(label)}</span> '
            f'<span style="color:var(--mute);font-family:JetBrains Mono,monospace;font-size:11.5px;">'
            f'{fmt_money(val)} · {val/total*100:.1f}%</span></span>'
        )
    return f'<div class="legend">{"".join(parts)}</div>'


def render(cost_rows, report_rows, cost_mode, sub_cash, repo_label):
    total = sum(float(r.get("cost_usd", 0) or 0) for r in cost_rows)
    sources = source_totals(cost_rows)
    issues = issue_totals(cost_rows)
    days = daily_totals(cost_rows)
    sessions = len(cost_rows)
    avg_session = total / sessions if sessions else 0
    avg_day = total / len(days) if days else 0
    dominant_source = sources[0][0] if sources else "n/a"
    window = ""
    if days:
        window = f"{days[0][0]} → {days[-1][0]}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    plan_banner = ""
    if cost_mode == "subscription":
        ratio_html = ""
        if sub_cash:
            ratio_html = (
                f" Subscription cash spent: <span class='mono'>{fmt_money(sub_cash)}</span>. "
                f"API-equivalent for the same work: <span class='mono'>{fmt_money(total)}</span> "
                f"= <strong>{total/sub_cash:.1f}× leverage</strong>."
            )
        plan_banner = (
            f'<div class="plan-banner"><span class="label">Heads up</span>'
            f'Subscription plan in use. Dollar figures below are <strong>retail-equivalents</strong> '
            f'— what the same work would cost on pay-as-you-go API rates — not your actual bill.'
            f'{ratio_html}</div>'
        )

    method = (
        '<details class="panel" style="background:#dbeafe;border-left:4px solid var(--accent);">'
        '<summary style="cursor:pointer;font-family:JetBrains Mono,monospace;font-size:11px;'
        'text-transform:uppercase;letter-spacing:0.08em;color:var(--accent);font-weight:600;">'
        '+ How the cost is calculated</summary>'
        '<div style="margin-top:14px;">'
        '<p>Anthropic charges per <strong>token</strong> (~4 chars / ¾ word). Token counts come '
        'from the JSONL transcripts Claude Code writes for every session. Same numbers Anthropic bills against.</p>'
        '<p>Four token types, four prices (Opus 4.7 list):</p>'
        '<ul style="font-size:13px;line-height:1.6;">'
        '<li><strong>Input</strong> = $15 / MTok (base)</li>'
        '<li><strong>Output</strong> = $75 / MTok (5× input — generating costs more than reading)</li>'
        '<li><strong>Cache read</strong> = $1.50 / MTok (0.1× input — cheap reuse)</li>'
        '<li><strong>Cache write 5m / 1h</strong> = $18.75 / MTok (1.25× input — one-time setup)</li>'
        '</ul>'
        '<p>Per-session cost = Σ (tokens × rate ÷ 1M) across all four types. '
        'Rate table lives in <code>src/avt/spend.py</code> — update when Anthropic publishes new prices.</p>'
        '<p>Non-Claude sources (Anthropic API CSV, Copilot seats, vendor CSV) use their own rate cards. '
        'Cross-vendor totals are sums of cash-equivalent USD across all sources.</p>'
        '</div></details>'
    )

    kpis = (
        '<div class="kpis">'
        f'<div class="kpi accent"><div class="label">Total spend</div>'
        f'<div class="value">{fmt_money(total)}</div>'
        f'<div class="note">{fmt_money(avg_day)} / day average</div></div>'
        f'<div class="kpi teal"><div class="label">Sessions / rows</div>'
        f'<div class="value">{fmt_int(sessions)}</div>'
        f'<div class="note">{fmt_money(avg_session)} avg per row</div></div>'
        f'<div class="kpi purple"><div class="label">Sources</div>'
        f'<div class="value">{len(sources)}</div>'
        f'<div class="note">dominant: {html.escape(dominant_source)}</div></div>'
        f'<div class="kpi amber"><div class="label">Attributed issues</div>'
        f'<div class="value">{fmt_int(len(issues))}</div>'
        f'<div class="note">top: #{html.escape(issues[0][0]) if issues else "n/a"}</div></div>'
        '</div>'
    )

    daily_panel = (
        '<div class="panel"><h2>Daily spend</h2>'
        f'<p class="panel-sub">USD per UTC day across all enabled sources. Window: {window}.</p>'
        f'{bar_svg(days)}</div>'
    )

    source_panel = (
        '<div class="panel"><h2>Spend by source</h2>'
        '<p class="panel-sub">Where the money goes across vendors.</p>'
        f'{stacked_svg(sources)}{legend(sources)}</div>'
    )

    if issues:
        rows_html = "".join(
            f'<tr><td class="key">#{html.escape(k)}</td>'
            f'<td class="num">{v["sessions"]}</td>'
            f'<td class="num">{fmt_money(v["cost"])}</td></tr>'
            for k, v in issues[:15]
        )
        issues_panel = (
            '<div class="panel"><h2>Top issues by spend</h2>'
            '<p class="panel-sub">Attribution via branch name and commit references.</p>'
            '<table><thead><tr><th>Issue</th><th class="num">Sessions</th><th class="num">Spend</th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>'
        )
    else:
        issues_panel = ""

    value_panel = ""
    if report_rows:
        value_rows = []
        for r in report_rows[:15]:
            issue = r.get("issue") or ""
            cost = float(r.get("cost_usd", 0) or 0)
            value = float(r.get("value_score", 0) or 0)
            ratio = float(r.get("ratio", 0) or 0)
            value_rows.append(
                f'<tr><td class="key">#{html.escape(issue)}</td>'
                f'<td class="num">{fmt_money(cost)}</td>'
                f'<td class="num">{fmt_int(int(value))}</td>'
                f'<td class="num">{ratio:.2f}</td></tr>'
            )
        value_panel = (
            '<div class="panel"><h2>Cost vs value</h2>'
            '<p class="panel-sub">Value score is a placeholder until product telemetry lands. '
            'Treat as relative, not absolute.</p>'
            '<table><thead><tr><th>Issue</th><th class="num">Cost</th>'
            '<th class="num">Value score</th><th class="num">Ratio</th></tr></thead>'
            f'<tbody>{"".join(value_rows)}</tbody></table></div>'
        )

    html_out = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(repo_label)} — AI cost &amp; value report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body>
<div class="topbar">
<span class="brand">{html.escape(repo_label)}<span class="dim">·</span> ai cost <span class="dim">/ value</span></span>
<span class="spacer"></span>
<span class="generated">generated {now}</span>
</div>
<div class="wrap">
<div class="kicker">ai-value-tracker</div>
<h1>AI cost &amp; value report</h1>
<p class="subtitle"><strong>{fmt_int(sessions)}</strong> rows · <strong>{len(sources)}</strong> sources · window {window or "n/a"}. Dominant source: <strong>{html.escape(dominant_source)}</strong>.</p>
{plan_banner}
{method}
{kpis}
{daily_panel}
{source_panel}
{issues_panel}
{value_panel}
<div class="footer">
<p>Source: <code>avt-cost</code> output. Regenerate: <code>avt-html --cost out/cost.csv --report out/report.csv --out report.html</code></p>
<p>Pricing in <code>src/avt/spend.py</code>. Method explainer above.</p>
</div>
</div></body></html>"""
    return html_out


def main():
    ap = argparse.ArgumentParser(description="Render single-page HTML cost-and-value report.")
    ap.add_argument("--cost", required=True, help="avt-cost CSV path.")
    ap.add_argument("--report", default=None, help="avt-report CSV path (optional).")
    ap.add_argument("--out", required=True, help="HTML output path.")
    ap.add_argument("--cost-mode", choices=["api", "subscription"], default="api")
    ap.add_argument("--sub-cash", type=float, default=None)
    ap.add_argument("--label", default="Harris · Wraith", help="Topbar label.")
    args = ap.parse_args()

    cost_rows = read_csv(args.cost)
    report_rows = read_csv(args.report) if args.report else []
    out = render(cost_rows, report_rows, args.cost_mode, args.sub_cash, args.label)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write(out)
    print(f"Wrote {args.out} ({len(out):,} bytes, {len(cost_rows)} cost rows, {len(report_rows)} value rows)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
