---
name: gsc-candlestick-report
description: Generate an HTML candlestick SEO report from Google Search Console data. Use this skill whenever the user asks for a keyword ranking report, candlestick chart, monthly SEO report, position tracking visualisation, or wants to see how their keywords are trending over time. Also trigger when they mention "candlestick", "OHLC", "ranking variance", or "monthly keyword positions". This skill assumes the user has already completed installation per README.md - if the GSC MCP is not connected, halt and point the user to README.md.
---

# GSC Candlestick SEO Report

Generate a self-contained HTML report showing keyword ranking trends as monthly candlestick charts. Each candle shows open, close, best and worst position - so direction AND volatility are visible at a glance.

## Prerequisite check (run first, every time)

Use ToolSearch with `select:mcp__gsc__get_advanced_search_analytics` to load the GSC tool schema.

- If the tool loads: setup is complete, proceed to Stage 1.
- If the tool fails to load: the GSC MCP is not connected. **STOP** and tell the user:

> The GSC MCP server is not installed or not connected. Please complete installation first - see the README at:
>
> https://github.com/garethdouble/gsc-candlestick-report#install
>
> Or just say "install GSC candlestick" and I will read the README and walk you through setup.
>
> Once installed and Claude Code is restarted, run /gsc-candlestick-report again.

Do not try to generate a report without the MCP.

---

## Stage 1: Project directory

Run `pwd`. Capture the result.

If the path is `$HOME` or some non-project location, ask the user:

> I need a project folder to save your report in. Want me to create `~/Documents/seo-reports/<sitename>`, or do you have a specific path in mind?

Wait for response. Create or `cd` to the chosen directory. Confirm with `pwd`.

If the path is already a sensible project directory, proceed.

---

## Stage 2: Keywords config

Run `ls keywords.yml` in the current directory.

**If `keywords.yml` exists:** read it. Validate `site_url` and a non-empty `keywords` section. Proceed to Stage 3.

**If missing:** ask the user:

> No `keywords.yml` found in this folder. Do you have a list of keywords ready, or should I help you build one?

If they have keywords: ask for the site URL and keyword list. Write `keywords.yml` in the format below.

If they need help: ask one at a time:
1. Website URL
2. Industry / what the business does
3. Top 3 services or products
4. City / region (if local)
5. Top 2 to 3 competitors

Suggest 10 to 20 starter keywords mixing branded, service, and intent. Confirm with the user. Write `keywords.yml`.

### keywords.yml format

```yaml
site_url: sc-domain:example.co.nz
months: 6
keywords:
  tier_1:
    - primary keyword
    - another primary keyword
  tier_2:
    - supporting keyword
  content:
    - blog query
```

A flat list is also valid:

```yaml
site_url: sc-domain:example.co.nz
months: 6
keywords:
  - keyword one
  - keyword two
```

If the user is unsure which `site_url` format to use, call `mcp__gsc__list_properties` and let them pick.

---

## Stage 3: Pull GSC data

For each keyword, call `mcp__gsc__get_advanced_search_analytics` with:
- `site_url`: from config
- `start_date`: N months ago (N = `months` from config, default 6)
- `end_date`: today
- `dimensions`: `"date"`
- `filter_dimension`: `"query"`
- `filter_operator`: `"equals"`
- `filter_expression`: the keyword
- `row_limit`: 500
- `data_state`: `"all"`

**Batch in parallel.** Up to 16 calls per batch.

---

## Stage 4: Build candlestick-data.json

**For 15 or fewer keywords:** write `candlestick-data.json` directly.

**For 16+ keywords:** delegate to a subagent. Have it write a Python script `build_candlestick_data.py` in the project dir that hardcodes the daily data, run it, and output `candlestick-data.json`. This keeps the data volume out of the main conversation context.

Strip rows where `impressions == 0` AND `position == 0` before writing - they are no-data days. Removes 30 to 60 percent of file size.

### Structure

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
    "content": []
  }
}
```

For flat keyword lists with no tiers, put everything under a single `"keywords"` key.

---

## Stage 5: Generate the HTML

```bash
python3 ~/.claude/skills/gsc-candlestick-report/scripts/generate_candlestick_report.py \
  ./candlestick-data.json \
  ./candlestick-report.html
```

If the skill is installed at a different path (e.g. `~/.claude/commands/`), adjust accordingly. The `scripts/` folder is always next to this SKILL.md.

---

## Stage 6: Open and summarise

```bash
open ./candlestick-report.html
```

Summarise in this structure:

**Improving** - keywords with green candles moving up. List the strongest movers with position ranges.

**High variance / Google testing** - keywords with wide wicks. Google is experimenting with placement - opportunity.

**Declining or stuck** - keywords that regressed or flatlined. Flag drop-offs.

**Action items** - 2 to 3 concrete next steps based on patterns.

---

## Notes

- The render script uses Python 3 stdlib only - no dependencies
- HTML report is fully self-contained (inline CSS, SVG charts, no CDN)
- Position scale is inverted: position 1 at the top
- Months with no data are skipped
- Hover any candle for detailed metrics
- Keywords with under 2 months of data show "NEW"
- The `build_candlestick_data.py` script in the project is reusable - on future runs you can skip Stage 3 if data is fresh enough
