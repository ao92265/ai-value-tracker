"""Render a single-page HTML cost-and-value report.

Editorial / data-journalism layout. Space Grotesk + IBM Plex Mono on paper-tone palette.

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


SEG_COLORS = ["#0a4f4a", "#0e6b64", "#c8602a", "#6b6457", "#a8362b", "#3a362f"]


CSS = """
:root{
  --paper:#f4efe6; --paper-2:#faf6ed;
  --ink:#161513; --ink-2:#3a362f; --muted:#6b6457;
  --rule:#d9d2c1; --rule-2:#c6bea8;
  --teal:#0a4f4a; --teal-2:#0e6b64;
  --terra:#c8602a; --red:#a8362b;
  --positive:#0a4f4a; --negative:#a8362b;
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;background:var(--paper);color:var(--ink);}
body{font-family:"Space Grotesk",system-ui,sans-serif;font-size:15px;line-height:1.5;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
.num,.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-feature-settings:"tnum" 1,"zero" 1;}
.page{max-width:1080px;margin:0 auto;padding:0 28px 80px;}

.ribbon{background:var(--ink);color:var(--paper);font-family:"IBM Plex Mono",monospace;
  font-size:12px;letter-spacing:0.04em;text-transform:uppercase;}
.ribbon-inner{max-width:1080px;margin:0 auto;padding:10px 28px;display:flex;gap:24px;
  align-items:center;flex-wrap:wrap;}
.ribbon .dot{width:8px;height:8px;border-radius:50%;background:var(--terra);
  display:inline-block;margin-right:8px;vertical-align:middle;}
.ribbon strong{color:#fff;font-weight:600;}
.ribbon .sep{opacity:0.4;}

.masthead{display:flex;justify-content:space-between;align-items:flex-end;
  border-bottom:2px solid var(--ink);padding:36px 0 18px;}
.masthead h1{font-size:32px;font-weight:700;letter-spacing:-0.02em;margin:0;line-height:1;}
.masthead h1 .accent{color:var(--teal);}
.masthead .meta{text-align:right;font-family:"IBM Plex Mono",monospace;font-size:11px;
  color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;line-height:1.6;}
.masthead .meta .edition{color:var(--ink);font-weight:600;}

.subhead{padding:14px 0 28px;border-bottom:1px solid var(--rule);
  font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.08em;display:flex;gap:28px;flex-wrap:wrap;}
.subhead span b{color:var(--ink);font-weight:600;}

.hero{padding:56px 0 48px;border-bottom:1px solid var(--rule);display:grid;
  grid-template-columns:1.5fr 1fr;gap:48px;align-items:end;}
.hero-label{font-family:"IBM Plex Mono",monospace;font-size:11px;text-transform:uppercase;
  letter-spacing:0.12em;color:var(--muted);margin-bottom:14px;}
.hero-figure{font-family:"Space Grotesk",sans-serif;font-weight:600;font-size:184px;
  line-height:0.85;letter-spacing:-0.045em;color:var(--ink);}
.hero-figure .x{color:var(--teal);font-size:0.55em;font-weight:500;
  vertical-align:0.18em;margin-left:0.04em;}
.hero-blurb{font-size:17px;line-height:1.45;color:var(--ink-2);max-width:32ch;
  padding-bottom:18px;}
.hero-blurb em{font-style:normal;color:var(--teal);font-weight:600;}
.hero-blurb .ratio-line{display:block;margin-top:14px;font-family:"IBM Plex Mono",monospace;
  font-size:13px;color:var(--muted);}

.kpis{display:grid;grid-template-columns:repeat(12,1fr);gap:0;
  border-bottom:1px solid var(--rule);}
.kpi{padding:28px 24px 28px 0;border-right:1px solid var(--rule);}
.kpi:last-child{border-right:none;padding-right:0;}
.kpi + .kpi{padding-left:24px;}
.kpi.k-wide{grid-column:span 4;} .kpi.k-med{grid-column:span 3;} .kpi.k-narrow{grid-column:span 2;}
.kpi .label{font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;}
.kpi .value{font-family:"IBM Plex Mono",monospace;font-size:32px;font-weight:500;
  color:var(--ink);letter-spacing:-0.01em;line-height:1;}
.kpi .sub{margin-top:8px;font-size:12px;color:var(--muted);}
.kpi .sub .pos{color:var(--positive);font-weight:600;}
.kpi .sub .neg{color:var(--negative);font-weight:600;}

.sec{padding:48px 0 8px;}
.sec-head{display:flex;align-items:baseline;gap:16px;margin-bottom:22px;}
.sec-num{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--terra);
  letter-spacing:0.1em;}
.sec-title{font-size:22px;font-weight:600;letter-spacing:-0.01em;margin:0;}
.sec-rule{flex:1;height:1px;background:var(--rule);}
.sec-note{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.08em;}
.sec-lede{font-size:16px;line-height:1.5;color:var(--ink-2);max-width:62ch;margin:0 0 28px;}

.daily{display:grid;grid-template-columns:2fr 1fr;gap:48px;align-items:stretch;}
.daily-bars{display:flex;flex-direction:column;gap:6px;}
.bar-row{display:grid;grid-template-columns:64px 1fr 80px;align-items:center;gap:14px;
  font-family:"IBM Plex Mono",monospace;font-size:12px;}
.bar-row .day{color:var(--muted);text-transform:uppercase;letter-spacing:0.05em;}
.bar-row .track{position:relative;height:18px;background:transparent;}
.bar-row .fill{height:100%;background:var(--teal);position:relative;}
.bar-row.peak .fill{background:var(--terra);}
.bar-row .amt{text-align:right;color:var(--ink);font-weight:500;}
.daily-side{border-left:1px solid var(--rule);padding-left:32px;display:flex;
  flex-direction:column;justify-content:center;gap:18px;}
.daily-stat .label{font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;}
.daily-stat .value{font-family:"IBM Plex Mono",monospace;font-size:24px;color:var(--ink);}
.daily-stat .value .small{font-size:13px;color:var(--muted);}

.alloc{display:flex;width:100%;height:44px;border:1px solid var(--ink);overflow:hidden;}
.alloc .seg{position:relative;border-right:1px solid var(--paper);}
.alloc .seg:last-child{border-right:none;}
.alloc .seg .pct{position:absolute;top:50%;left:10px;transform:translateY(-50%);
  font-family:"IBM Plex Mono",monospace;font-size:11px;color:#fff;font-weight:500;}
.alloc-legend{margin-top:14px;display:grid;grid-template-columns:repeat(4,1fr);gap:18px 24px;}
.leg{border-top:1px solid var(--rule);padding-top:12px;}
.leg .swatch{display:inline-block;width:10px;height:10px;margin-right:8px;vertical-align:1px;}
.leg .name{font-size:13px;font-weight:600;color:var(--ink);}
.leg .amt{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--muted);margin-top:4px;}

.cards{display:flex;flex-direction:column;gap:0;border-top:1px solid var(--rule);}
.card{display:grid;grid-template-columns:32px 1fr auto;gap:24px;align-items:center;
  padding:18px 8px;border-bottom:1px solid var(--rule);transition:background 120ms ease;}
.card:hover{background:var(--paper-2);}
.card .rank{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);}
.card .body{display:flex;flex-direction:column;gap:4px;min-width:0;}
.card .title{font-size:15px;font-weight:600;color:var(--ink);white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;}
.card .meta{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.06em;}
.card .right{text-align:right;display:flex;flex-direction:column;align-items:flex-end;gap:4px;}
.card .right .figure{font-family:"IBM Plex Mono",monospace;font-size:18px;color:var(--ink);}
.card .right .sub{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--muted);}

.cv-card{display:grid;grid-template-columns:32px 1.4fr 1fr 1fr auto;gap:24px;align-items:center;
  padding:18px 8px;border-bottom:1px solid var(--rule);transition:background 120ms ease;}
.cv-card:hover{background:var(--paper-2);}
.cv-card .label{font-family:"IBM Plex Mono",monospace;font-size:10px;color:var(--muted);
  text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;}
.cv-card .v{font-family:"IBM Plex Mono",monospace;font-size:14px;color:var(--ink);}
.cv-bar{position:relative;height:8px;background:var(--rule);margin-top:6px;}
.cv-bar .cost{position:absolute;left:0;top:0;height:100%;background:var(--ink);}
.cv-bar .value{position:absolute;left:0;top:0;height:100%;background:var(--teal);opacity:0.85;}
.cv-card .lev{font-family:"Space Grotesk",sans-serif;font-weight:600;font-size:24px;
  color:var(--teal);text-align:right;}
.cv-card .lev .small{font-size:13px;color:var(--muted);font-weight:500;}

.method{margin-top:48px;padding:32px;background:var(--paper-2);border:1px solid var(--rule);}
.method h3{font-size:13px;font-family:"IBM Plex Mono",monospace;text-transform:uppercase;
  letter-spacing:0.1em;color:var(--terra);margin:0 0 16px;font-weight:500;}
.method-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:32px;}
.method dt{font-size:14px;font-weight:600;color:var(--ink);margin-bottom:6px;}
.method dd{margin:0 0 14px;font-size:13px;color:var(--ink-2);line-height:1.5;}
.method .formula{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink);
  background:var(--paper);border:1px solid var(--rule);padding:6px 8px;
  display:inline-block;margin-top:4px;}

footer{margin-top:72px;padding-top:24px;border-top:2px solid var(--ink);display:flex;
  justify-content:space-between;align-items:flex-end;font-family:"IBM Plex Mono",monospace;
  font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:0.06em;}
footer .colophon{max-width:48ch;line-height:1.6;}
footer .pg{font-weight:600;color:var(--ink);font-size:14px;}

@media print{
  body{background:#fff;}
  .ribbon{background:#000;}
  .page{padding:0 16mm;}
  .card:hover,.cv-card:hover{background:transparent;}
  .hero-figure{font-size:140px;}
  .sec{page-break-inside:avoid;}
}
@media (max-width:760px){
  .page{padding:0 18px 60px;}
  .masthead{flex-direction:column;align-items:flex-start;gap:14px;}
  .masthead .meta{text-align:left;}
  .hero{grid-template-columns:1fr;gap:20px;padding:36px 0 32px;}
  .hero-figure{font-size:110px;}
  .kpis{grid-template-columns:repeat(2,1fr);}
  .kpi,.kpi + .kpi{padding:18px 12px;border-right:1px solid var(--rule);
    border-bottom:1px solid var(--rule);}
  .kpi.k-wide,.kpi.k-med,.kpi.k-narrow{grid-column:span 1;}
  .daily{grid-template-columns:1fr;gap:24px;}
  .daily-side{border-left:none;border-top:1px solid var(--rule);padding-left:0;
    padding-top:20px;flex-direction:row;flex-wrap:wrap;gap:24px;}
  .alloc-legend{grid-template-columns:repeat(2,1fr);}
  .cv-card{grid-template-columns:24px 1fr auto;gap:14px;}
  .cv-card .col-cost,.cv-card .col-value{display:none;}
  .method-grid{grid-template-columns:1fr;}
  footer{flex-direction:column;align-items:flex-start;gap:14px;}
}
"""


def fmt_money(n):
    if n >= 1000:
        return f"${n:,.0f}"
    return f"${n:,.2f}"


def fmt_int(n):
    return f"{n:,}"


def read_csv(path):
    if not path or not os.path.isfile(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def daily_totals(rows):
    by_day = defaultdict(float)
    for r in rows:
        started = (r.get("started") or "")[:10]
        if not started:
            continue
        try:
            cost = float(r.get("cost_usd", 0) or 0)
        except ValueError:
            continue
        by_day[started] += cost
    return sorted(by_day.items())


def source_totals(rows):
    by_src = defaultdict(lambda: {"cost": 0.0, "calls": 0})
    for r in rows:
        try:
            cost = float(r.get("cost_usd", 0) or 0)
        except ValueError:
            cost = 0.0
        s = r.get("source", "unknown")
        by_src[s]["cost"] += cost
        by_src[s]["calls"] += 1
    return sorted(by_src.items(), key=lambda x: x[1]["cost"], reverse=True)


def user_totals(rows):
    by_user = defaultdict(lambda: {"cost": 0.0, "sessions": 0, "projects": set()})
    for r in rows:
        u = (r.get("user") or "").strip()
        if not u:
            continue
        try:
            cost = float(r.get("cost_usd", 0) or 0)
        except ValueError:
            cost = 0.0
        by_user[u]["cost"] += cost
        by_user[u]["sessions"] += 1
        notes = r.get("notes") or ""
        if notes:
            by_user[u]["projects"].add(notes[:24])
    return sorted(by_user.items(), key=lambda x: x[1]["cost"], reverse=True)


def issue_totals(rows):
    by_issue = defaultdict(lambda: {"cost": 0.0, "sessions": 0, "title": ""})
    for r in rows:
        attr = r.get("attributed_to", "")
        if not attr.startswith("issue:"):
            continue
        key = attr.split(":", 1)[1]
        try:
            cost = float(r.get("cost_usd", 0) or 0)
        except ValueError:
            cost = 0.0
        by_issue[key]["cost"] += cost
        by_issue[key]["sessions"] += 1
        if not by_issue[key]["title"]:
            by_issue[key]["title"] = (r.get("notes") or "")[:90]
    return sorted(by_issue.items(), key=lambda x: x[1]["cost"], reverse=True)


def short_day(iso):
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%a %d").upper()
    except Exception:
        return iso[-5:]


def render(cost_rows, report_rows, cost_mode, sub_cash, repo_label):
    total = sum(float(r.get("cost_usd", 0) or 0) for r in cost_rows)
    sources = source_totals(cost_rows)
    issues = issue_totals(cost_rows)
    users = user_totals(cost_rows)
    days = daily_totals(cost_rows)
    sessions = len(cost_rows)
    tasks = len(issues)
    cost_per_task = total / tasks if tasks else 0
    cost_per_session = total / sessions if sessions else 0

    window = f"{days[0][0]} → {days[-1][0]}" if days else "n/a"
    now = datetime.now(timezone.utc)

    # Hero: leverage if subscription, total spend if api
    if cost_mode == "subscription" and sub_cash:
        hero_num = f"{total / sub_cash:.0f}"
        hero_unit = "×"
        hero_label = "Leverage ratio — value delivered per dollar of subscription"
        hero_blurb = (
            f"For every <em>$1</em> of subscription cash, the team captured "
            f"<em>{fmt_money(total/sub_cash)}</em> in token-equivalent work this window. "
            f"Hero number is illustrative leverage — real cash is the flat subscription."
            f"<span class='ratio-line'>{fmt_money(total)} token-equiv &nbsp;÷&nbsp; "
            f"{fmt_money(sub_cash)} subscription</span>"
        )
    else:
        hero_num = fmt_money(total).replace("$", "")
        hero_unit = "$"
        hero_label = "Total spend — pay-as-you-go cash basis"
        hero_blurb = (
            f"<em>{sessions}</em> sessions across <em>{len(sources)}</em> sources, "
            f"window {window}."
            f"<span class='ratio-line'>cost per session: {fmt_money(cost_per_session)}</span>"
        )

    # Ribbon
    if cost_mode == "subscription":
        ribbon = (
            '<div class="ribbon" role="note" aria-label="Subscription mode">'
            '<div class="ribbon-inner">'
            '<span><span class="dot"></span><strong>Subscription mode</strong></span>'
            '<span class="sep">/</span>'
            f'<span>Cash basis &nbsp;<strong>{fmt_money(sub_cash or 0)} / month</strong></span>'
            '<span class="sep">/</span>'
            f'<span>Dominant: <strong>{html.escape(sources[0][0]) if sources else "n/a"}</strong></span>'
            '<span class="sep">/</span>'
            f'<span>Window <strong>{window}</strong></span>'
            '</div></div>'
        )
    else:
        ribbon = (
            '<div class="ribbon" role="note" aria-label="API mode">'
            '<div class="ribbon-inner">'
            '<span><span class="dot"></span><strong>API mode (cash)</strong></span>'
            '<span class="sep">/</span>'
            f'<span>Sources: <strong>{len(sources)}</strong></span>'
            '<span class="sep">/</span>'
            f'<span>Window <strong>{window}</strong></span>'
            '</div></div>'
        )

    # KPI strip
    kpis = (
        '<section class="kpis" aria-label="Key performance indicators">'
        '<div class="kpi k-wide">'
        '<div class="label">' + ("Total spend (cash)" if cost_mode == "subscription" else "Total spend") + '</div>'
        f'<div class="value">{fmt_money(sub_cash if cost_mode == "subscription" and sub_cash else total)}</div>'
        f'<div class="sub">' + ("Flat subscription · no per-token overage" if cost_mode == "subscription"
                                 else f"{sessions} sessions · {len(sources)} sources") + '</div>'
        '</div>'
        '<div class="kpi k-med">'
        '<div class="label">Token-equivalent</div>'
        f'<div class="value">{fmt_money(total)}</div>'
        f'<div class="sub">If billed per-token over window</div>'
        '</div>'
        '<div class="kpi k-med">'
        '<div class="label">Cost / task</div>'
        f'<div class="value">{fmt_money(cost_per_task)}</div>'
        f'<div class="sub">{tasks} attributed tasks (productivity)</div>'
        '</div>'
        '<div class="kpi k-narrow">'
        '<div class="label">Sessions</div>'
        f'<div class="value">{fmt_int(sessions)}</div>'
        f'<div class="sub">{fmt_money(cost_per_session)} avg / session</div>'
        '</div>'
        '</section>'
    )

    # Daily horizontal bars (last up to 14 days)
    show_days = days[-14:] if len(days) > 14 else days
    if show_days:
        max_day = max(c for _, c in show_days) or 1
        peak_day, peak_cost = max(show_days, key=lambda x: x[1])
        bars = []
        for day, cost in show_days:
            pct = (cost / max_day) * 100
            peak_class = " peak" if day == peak_day else ""
            bars.append(
                f'<div class="bar-row{peak_class}">'
                f'<span class="day">{html.escape(short_day(day))}</span>'
                f'<div class="track"><div class="fill" style="width:{pct:.0f}%"></div></div>'
                f'<span class="amt">{fmt_money(cost)}</span></div>'
            )
        daily_bars = "".join(bars)
        daily_total = sum(c for _, c in show_days)
        try:
            pk_short = datetime.fromisoformat(peak_day).strftime("%a %d")
        except Exception:
            pk_short = peak_day
        side = (
            '<aside class="daily-side">'
            f'<div class="daily-stat"><div class="label">Window total</div>'
            f'<div class="value">{fmt_money(daily_total)}</div></div>'
            f'<div class="daily-stat"><div class="label">Peak day</div>'
            f'<div class="value">{pk_short} <span class="small">{fmt_money(peak_cost)}</span></div></div>'
            f'<div class="daily-stat"><div class="label">Active days</div>'
            f'<div class="value">{len(show_days)} <span class="small">of {len(days)}</span></div></div>'
            '</aside>'
        )
    else:
        daily_bars = ""
        side = ""

    daily_panel = (
        '<section class="sec" aria-labelledby="sec-daily">'
        '<div class="sec-head">'
        '<span class="sec-num">§ 01</span>'
        '<h2 class="sec-title" id="sec-daily">Daily token-equivalent spend</h2>'
        '<span class="sec-rule"></span>'
        f'<span class="sec-note">USD · {len(show_days)} days</span>'
        '</div>'
        '<p class="sec-lede">Daily token-equivalent cost from the unified cost CSV. '
        'On a flat subscription this is virtual — useful for routing and capacity, not finance.</p>'
        f'<div class="daily"><div class="daily-bars" role="img" aria-label="Daily bars">{daily_bars}</div>{side}</div>'
        '</section>'
    )

    # Source allocation
    if sources:
        src_total = sum(s["cost"] for _, s in sources) or 1
        segs = []
        legs = []
        for i, (name, info) in enumerate(sources[:6]):
            pct = info["cost"] / src_total * 100
            color = SEG_COLORS[i % len(SEG_COLORS)]
            segs.append(
                f'<div class="seg" style="width:{pct:.1f}%;background:{color};">'
                f'<span class="pct">{pct:.0f}%</span></div>'
            )
            legs.append(
                f'<div class="leg"><span class="swatch" style="background:{color};"></span>'
                f'<span class="name">{html.escape(name)}</span>'
                f'<div class="amt">{fmt_money(info["cost"])} · {info["calls"]} rows</div></div>'
            )
        source_panel = (
            '<section class="sec" aria-labelledby="sec-source">'
            '<div class="sec-head">'
            '<span class="sec-num">§ 02</span>'
            '<h2 class="sec-title" id="sec-source">Where the spend went</h2>'
            '<span class="sec-rule"></span>'
            '<span class="sec-note">By source</span>'
            '</div>'
            '<p class="sec-lede">Allocation of token-equivalent spend across instrumented sources.</p>'
            f'<div class="alloc" role="img">{"".join(segs)}</div>'
            f'<div class="alloc-legend">{"".join(legs)}</div>'
            '</section>'
        )
    else:
        source_panel = ""

    # Top issues (productivity-oriented)
    if issues:
        cards = []
        for i, (issue, info) in enumerate(issues[:6], 1):
            pct = info["cost"] / total * 100 if total else 0
            title = info["title"] or f"Issue #{issue}"
            cards.append(
                '<div class="card" role="listitem">'
                f'<span class="rank">{i:02d}</span>'
                '<div class="body">'
                f'<div class="title">#{html.escape(issue)} · {html.escape(title)}</div>'
                f'<div class="meta">{info["sessions"]} sessions · {fmt_money(info["cost"]/info["sessions"])} avg</div>'
                '</div>'
                '<div class="right">'
                f'<div class="figure">{fmt_money(info["cost"])}</div>'
                f'<div class="sub">{pct:.1f}% of total</div>'
                '</div></div>'
            )
        issues_panel = (
            '<section class="sec" aria-labelledby="sec-issues">'
            '<div class="sec-head">'
            '<span class="sec-num">§ 03</span>'
            '<h2 class="sec-title" id="sec-issues">Top issues by cost</h2>'
            '<span class="sec-rule"></span>'
            f'<span class="sec-note">Top {min(6, len(issues))} of {len(issues)}</span>'
            '</div>'
            '<p class="sec-lede">Costliest threads in the window. Productivity signal: '
            'high-cost issues with high session counts are candidates for summarisation or scope split.</p>'
            f'<div class="cards" role="list">{"".join(cards)}</div>'
            '</section>'
        )
    else:
        issues_panel = ""

    # Top users (team attribution)
    if users:
        ucards = []
        for i, (u, info) in enumerate(users[:6], 1):
            pct = info["cost"] / total * 100 if total else 0
            label = u.split("@")[0] if "@" in u else u
            ucards.append(
                '<div class="card" role="listitem">'
                f'<span class="rank">{i:02d}</span>'
                '<div class="body">'
                f'<div class="title">{html.escape(label)}</div>'
                f'<div class="meta">{html.escape(u)} · {info["sessions"]} sessions · '
                f'{len(info["projects"])} contexts</div>'
                '</div>'
                '<div class="right">'
                f'<div class="figure">{fmt_money(info["cost"])}</div>'
                f'<div class="sub">{pct:.1f}% of total</div>'
                '</div></div>'
            )
        users_panel = (
            '<section class="sec" aria-labelledby="sec-users">'
            '<div class="sec-head">'
            '<span class="sec-num">§ 04</span>'
            '<h2 class="sec-title" id="sec-users">Top users by cost</h2>'
            '<span class="sec-rule"></span>'
            f'<span class="sec-note">{len(users)} contributors</span>'
            '</div>'
            '<p class="sec-lede">Attribution via <code>git config user.email</code> at the session cwd. '
            'Each contributor running the tool against their own machine produces a team-wide picture.</p>'
            f'<div class="cards" role="list">{"".join(ucards)}</div>'
            '</section>'
        )
    else:
        users_panel = ""

    # Cost vs value
    value_panel = ""
    if report_rows:
        cv_cards = []
        for i, r in enumerate(report_rows[:6], 1):
            issue = r.get("issue") or ""
            cost = float(r.get("cost_usd", 0) or 0)
            value = float(r.get("value_score", 0) or 0)
            ratio = float(r.get("ratio", 0) or 0)
            cost_pct = (cost / total * 100) if total else 0
            value_pct = min(100, (value / max(cost, 1)) * 5)
            cv_cards.append(
                '<div class="cv-card">'
                f'<span class="rank">{i:02d}</span>'
                '<div>'
                '<div class="label">Issue</div>'
                f'<div class="v"><strong style="font-family:\'Space Grotesk\',sans-serif;font-size:15px;">'
                f'#{html.escape(issue)}</strong></div>'
                f'<div class="cv-bar"><div class="cost" style="width:{cost_pct:.1f}%"></div>'
                f'<div class="value" style="width:{value_pct:.1f}%"></div></div>'
                '</div>'
                f'<div class="col-cost"><div class="label">Cost</div><div class="v">{fmt_money(cost)}</div></div>'
                f'<div class="col-value"><div class="label">Value score</div><div class="v">{fmt_int(int(value))}</div></div>'
                f'<div class="lev">{ratio:.1f}<span class="small">×</span></div>'
                '</div>'
            )
        value_panel = (
            '<section class="sec" aria-labelledby="sec-cv">'
            '<div class="sec-head">'
            '<span class="sec-num">§ 05</span>'
            '<h2 class="sec-title" id="sec-cv">Cost vs value, by issue</h2>'
            '<span class="sec-rule"></span>'
            '<span class="sec-note">Leverage per issue</span>'
            '</div>'
            '<p class="sec-lede">Value score from <span class="mono">report.csv</span>. '
            'Placeholder formula until product telemetry lands — treat as directional.</p>'
            f'<div class="cards">{"".join(cv_cards)}</div>'
            '</section>'
        )

    method = (
        '<section class="method" aria-labelledby="sec-method">'
        '<h3 id="sec-method">Method &amp; assumptions</h3>'
        '<div class="method-grid">'
        '<dl>'
        '<dt>Cost (cash)</dt>'
        '<dd>Subscription mode: flat monthly outlay via <span class="mono">--sub-cash</span>. '
        'API mode: sum of per-token costs in <span class="mono">cost.csv</span>.</dd>'
        '<dt>Token-equivalent</dt>'
        '<dd>What the same usage would cost on per-token rates.'
        '<div class="formula">tok_eq = Σ(tokens × unit_price)</div></dd>'
        '</dl>'
        '<dl>'
        '<dt>Productivity</dt>'
        '<dd>Tasks resolved = unique issues attributed via branch or commit ref. '
        'Cost per task = total ÷ tasks.</dd>'
        '<dt>Leverage</dt>'
        '<dd>Token-equivalent ÷ subscription cash. Useful for sub-vs-API decision.</dd>'
        '</dl>'
        '<dl>'
        '<dt>Value</dt>'
        '<dd>Placeholder formula in <span class="mono">avt-report</span>. '
        'Replace with product-side telemetry (see telemetry spec).</dd>'
        '<dt>Caveats</dt>'
        '<dd>Token prices in <span class="mono">spend.py</span> are list-rate; '
        'enterprise discounts not modelled. Branch attribution ~95% accurate.</dd>'
        '</dl>'
        '</div></section>'
    )

    out = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(repo_label)} — AI Value Tracker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body>
{ribbon}
<div class="page">
<header class="masthead">
<h1>AI Value <span class="accent">Tracker</span></h1>
<div class="meta">
<div class="edition">{html.escape(repo_label)}</div>
<div>Generated {now.strftime("%Y-%m-%d %H:%M UTC")}</div>
<div>avt-html · v0.2.0</div>
</div>
</header>
<div class="subhead" aria-label="Report metadata">
<span><b>Window</b> &nbsp; {window}</span>
<span><b>Sources</b> &nbsp; {len(sources)}</span>
<span><b>Sessions</b> &nbsp; {fmt_int(sessions)}</span>
<span><b>Tasks resolved</b> &nbsp; {fmt_int(tasks)}</span>
</div>
<section class="hero" aria-labelledby="hero-h">
<div>
<div class="hero-label" id="hero-h">{hero_label}</div>
<div class="hero-figure">{hero_num}<span class="x">{hero_unit}</span></div>
</div>
<p class="hero-blurb">{hero_blurb}</p>
</section>
{kpis}
{daily_panel}
{source_panel}
{issues_panel}
{users_panel}
{value_panel}
{method}
<footer>
<div class="colophon">Produced by <strong style="color:var(--ink)">avt-html</strong>. Data: <span class="mono">cost.csv</span> (avt-cost), <span class="mono">report.csv</span> (avt-report).</div>
<div class="pg">— 01 / 01 —</div>
</footer>
</div></body></html>"""
    return out


def main():
    ap = argparse.ArgumentParser(description="Render single-page HTML cost-and-value report.")
    ap.add_argument("--cost", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cost-mode", choices=["api", "subscription"], default="api")
    ap.add_argument("--sub-cash", type=float, default=None)
    ap.add_argument("--label", default="AI Value Tracker")
    args = ap.parse_args()

    cost_rows = read_csv(args.cost)
    report_rows = read_csv(args.report) if args.report else []
    out = render(cost_rows, report_rows, args.cost_mode, args.sub_cash, args.label)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write(out)
    print(f"Wrote {args.out} ({len(out):,} bytes, {len(cost_rows)} cost rows, "
          f"{len(report_rows)} value rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
