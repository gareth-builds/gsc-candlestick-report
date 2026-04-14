---
name: gsc-candlestick-report
description: Generate an HTML candlestick SEO report from Google Search Console data. Use this skill whenever the user asks for a keyword ranking report, candlestick chart, monthly SEO report, position tracking visualisation, or wants to see how their keywords are trending over time. Also trigger when they mention "candlestick", "OHLC", "ranking variance", or "monthly keyword positions". Reads configuration from keywords.yml in the current project directory, with CLAUDE.md as a fallback.
---

# GSC Candlestick SEO Report

Generate a standalone HTML report showing keyword ranking trends using candlestick charts. Each keyword gets a monthly candle showing open, close, best and worst positions - making it easy to see both direction and stability at a glance.

## Why candlesticks for SEO

A single average position number is misleading. Daily rankings fluctuate significantly across devices and locations. Candlestick charts show the full picture:
- **Body (open to close):** Did the keyword improve or decline during the month?
- **Wicks (high to low):** How much variance was there? Longer wicks = more instability
- **Green candle:** Position improved (close better than open)
- **Red candle:** Position declined (close worse than open)
- **Goal:** Move candles up (lower position numbers) AND make them thinner (less variance)

## Prerequisites

Before running, confirm the user has:
1. The GSC MCP server connected (provides `mcp__gsc__*` tools). If `mcp__gsc__get_advanced_search_analytics` is not available via ToolSearch, stop and tell the user to install the MCP first (see README.md in this skill directory).
2. Access to at least one Search Console property.

## Workflow

### Step 1: Gather configuration

Look for configuration in this order:

**A) `keywords.yml` in the current project directory (preferred).**

Read it. It contains:
- `site_url`: the GSC property (e.g. `sc-domain:example.co.nz` or `https://www.example.co.nz/`)
- `months`: history window, default 6
- `keywords`: either a flat list OR a dict of tiers (e.g. `tier_1`, `tier_2`, `tier_3`, `content`)

**B) `CLAUDE.md` in the current project directory (fallback).**

If `keywords.yml` does not exist, look in CLAUDE.md for:
- A site URL or `sc-domain:` reference
- Keyword tables or lists, optionally organised by tier

**C) Ask the user.**

If neither file is found, prompt the user to either create `keywords.yml` (show them `keywords.example.yml` in this skill directory as a template) or paste their keywords into the conversation.

If the user passes keywords directly in their prompt, those override everything above.

If `site_url` is ambiguous or missing, call `mcp__gsc__list_properties` and ask the user which one to use.

### Step 2: Pull daily position data from GSC

You need the `mcp__gsc__get_advanced_search_analytics` tool. If it is not loaded yet, use ToolSearch to fetch its schema first.

For each target keyword, call with:
- `site_url`: the GSC property from config
- `start_date`: N months ago, where N is `months` from config (default 6)
- `end_date`: today
- `dimensions`: `"date"`
- `filter_dimension`: `"query"`
- `filter_operator`: `"equals"`
- `filter_expression`: the keyword
- `row_limit`: 500
- `data_state`: `"all"`

**Batch these calls in parallel.** Make as many parallel MCP tool calls as possible (up to 16 at a time) to minimise total time. For 29 keywords, that is 2 batches.

### Step 3: Assemble the data file

This is the most context-intensive step. The approach depends on keyword count:

**For 15 or fewer keywords:** Write `candlestick-data.json` directly in the project directory.

**For 16+ keywords:** Delegate to a subagent using the Agent tool. The subagent should:
1. Write a Python script at `<project-dir>/build_candlestick_data.py` that hardcodes all the daily data from the GSC responses
2. Run it to output `candlestick-data.json`
3. This keeps the large data volume out of the main conversation context

When briefing the subagent, pass it:
- The site URL and report date
- The keyword tier assignments
- The raw daily_data arrays for each keyword (from the GSC responses you already fetched)

**Data filtering:** Before writing, strip rows where `impressions == 0` AND `position == 0`. These are days with no data. The report script already filters at MIN_IMPRESSIONS=5, so low-impression days are excluded from candle calculations automatically. Removing zero rows reduces file size by 30 to 60 percent.

**JSON structure:**

```json
{
  "site_url": "example.co.nz",
  "report_date": "2026-04-15",
  "keywords": {
    "tier_1": [
      {
        "keyword": "drain unblockers",
        "daily_data": [
          {"date": "2026-03-16", "clicks": 1, "impressions": 50, "ctr": 0.02, "position": 9.5}
        ]
      }
    ],
    "tier_2": [],
    "tier_3": [],
    "content": []
  }
}
```

If the config uses a flat keyword list (no tiers), put everything under a single key called `"keywords"` as the tier name. The report script handles any tier key names.

Each keyword's `daily_data` comes from the GSC API response `rows`. If a keyword returned no data, include it with an empty `daily_data` array.

### Step 4: Generate the HTML report

Run the Python script that ships with this skill:

```bash
python3 ~/.claude/skills/gsc-candlestick-report/scripts/generate_candlestick_report.py \
  <project-dir>/candlestick-data.json \
  <project-dir>/candlestick-report.html
```

If the skill was installed at a different path (e.g. `~/.claude/commands/`), adjust accordingly. The SKILL.md location is self-describing - use the `scripts/` folder next to this file.

### Step 5: Open and summarise

Open the generated HTML file:

```bash
open <project-dir>/candlestick-report.html
```

Tell the user where the files are saved, then provide a structured summary:

**Improving** - Keywords with green candles moving up (list the strongest movers with position ranges)

**High variance / Google testing** - Keywords with wide wicks where Google is experimenting with placement. These are opportunities - the algorithm is considering the page for better positions

**Declining or stuck** - Keywords that regressed or flatlined. Flag any that dropped off significantly

**Action items** - Based on the patterns, suggest 2 to 3 specific next steps (e.g. "investigate why X dropped in April", "Y is close to page 1, push with internal linking")

## Notes

- The script has zero external dependencies - just Python 3 stdlib
- The HTML report is fully self-contained (inline CSS, SVG charts, no CDN dependencies)
- Position scale is inverted: position 1 at the top of each chart
- Months with no data for a keyword are skipped (no candle drawn)
- Hover over any candle body to see detailed metrics (position OHLC, impressions, clicks, CTR, variance)
- Keywords with fewer than 2 months of data show "NEW" instead of improving/declining
- The `build_candlestick_data.py` script left in the project directory is reusable for future runs
