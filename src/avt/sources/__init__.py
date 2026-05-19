"""Cost source adapters.

Every source module exposes a `read(...)` function returning a list of dicts
with this common shape:

    {
        "source":         "claude-code" | "anthropic-api" | "copilot" | ...,
        "started":        "2026-05-01T00:00:00Z" | "2026-05" | "",
        "cost_usd":       float,
        "attributed_to":  "issue:1234" | "user:alice" | "team:platform" | "tenant:acme",
        "user":           "alice@example.com" (best-effort via git config),
        "units":          int (tokens / seats / resolutions / minutes),
        "notes":          str,
    }

avt.cost calls every enabled source, merges, writes one CSV.
"""

ROW_FIELDS = ["source", "started", "cost_usd", "attributed_to", "user", "units", "notes"]
