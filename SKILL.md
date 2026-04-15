---
name: gsc-candlestick-report
description: Generate an HTML candlestick SEO report from Google Search Console data. Use this skill whenever the user asks for a keyword ranking report, candlestick chart, monthly SEO report, position tracking visualisation, or wants to see how their keywords are trending over time. Also trigger when they mention "candlestick", "OHLC", "ranking variance", or "monthly keyword positions". This skill assumes the user has already completed installation per README.md - if credentials are missing, halt and point the user to README.md.
---

# GSC Candlestick SEO Report

Generate a self-contained HTML report showing keyword ranking trends as monthly candlestick charts. Each candle shows open, close, best and worst position — direction AND volatility are visible at a glance.

The skill talks to the Google Search Console API directly (no MCP round-trip), so report generation for 20-30 keywords takes a few seconds and uses almost no conversation context.

---

## Prerequisite check (run first, every time)

Check that credentials exist before doing anything else. Run:

```bash
ls ~/.config/gsc-candlestick/token.json \
   ~/Library/Application\ Support/mcp-gsc/token.json \
   ~/.config/gsc-candlestick/credentials.json \
   ~/Documents/gsc-secrets/client_secrets.json 2>/dev/null
```

If **at least one** of those files exists, setup is complete — proceed to Stage 1.

If **none** exist, STOP and tell the user:

> No GSC credentials found. Before first use you need to download a Google Cloud OAuth client JSON. Full setup (~5 min) is here:
>
> https://github.com/gareth-builds/gsc-candlestick-report#google-cloud-setup
>
> Once `credentials.json` is saved to `~/.config/gsc-candlestick/credentials.json`, rerun the skill. The first run will open a browser once to authorise, then all future runs are silent.

Do not try to generate a report without credentials.

---

## Stage 1: Project directory

Run `pwd`. Capture the result.

If the path is `$HOME` or some non-project location, ask the user:

> I need a project folder to save your report in. Want me to create `~/Documents/seo-reports/<sitename>`, or do you have a specific path in mind?

Wait for a response. Create or `cd` to the chosen directory. Confirm with `pwd`.

If the path is already a sensible project directory, proceed.

---

## Stage 2: Keywords config (ALWAYS confirm — never infer silently)

Run `ls keywords.yml` in the current directory.

### If `keywords.yml` exists

Read it. Validate `site_url` and a non-empty `keywords` section. Show the user a one-line summary ("found 27 keywords across tier_1, tier_2, tier_3, content — proceed?") and wait for confirmation before moving on. Proceed to Stage 3.

### If `keywords.yml` is missing

**Never auto-generate `keywords.yml` from context (CLAUDE.md, sitemaps, prior runs).** Even if an obvious keyword list exists elsewhere in the project, surface it and ask for confirmation first. Example:

> I didn't find `keywords.yml` in this folder. I did notice a target keyword list in your CLAUDE.md — want me to use those 27 keywords, or would you rather define your own?

Options when the user needs help building a list:

1. **They have keywords ready** — ask for the site URL and the list, write `keywords.yml` and show it back for approval.
2. **They want help** — ask one question at a time:
   - Website URL
   - Industry / what the business does
   - Top 3 services or products
   - City / region (if local)
   - Top 2 to 3 competitors

   Then suggest 10 to 20 starter keywords mixing branded, service and intent. Wait for confirmation before writing the file.

If the user is unsure which `site_url` format to use, call `mcp__gsc__list_properties` (if the GSC MCP is installed) or tell them:
- Domain property: `sc-domain:example.co.nz`
- URL-prefix property: `https://www.example.co.nz/`

### keywords.yml format

Tiered:

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

Flat list is also valid:

```yaml
site_url: sc-domain:example.co.nz
months: 6
keywords:
  - keyword one
  - keyword two
```

Tell the user where the file lives and how to edit it:

> `keywords.yml` is in the current project folder. Add or remove keywords any time and rerun the skill — no other setup needed.

---

## Stage 3: Fetch data and render the report (one command)

Build the dated output folder and run the fetcher + renderer. The fetcher hits the Google Search Console API directly, writes `candlestick-data.json`, then the renderer produces the HTML.

```bash
REPORT_DIR="./SEO_CandleStick/$(date +%Y-%m-%d)"
mkdir -p "$REPORT_DIR"
python3 ~/.claude/skills/gsc-candlestick-report/scripts/fetch_gsc_data.py \
  ./keywords.yml "$REPORT_DIR/candlestick-data.json"
python3 ~/.claude/skills/gsc-candlestick-report/scripts/generate_candlestick_report.py \
  "$REPORT_DIR/candlestick-data.json" "$REPORT_DIR/candlestick-report.html"
```

**Important — do NOT delegate to a subagent and do NOT paste the JSON contents into the conversation.** The fetcher writes straight to disk. Keeping the data out of LLM context is the whole point of this architecture — a 6-month × 30-keyword pull is ~4,000 rows and would blow through context if loaded.

If the fetcher is the user's first run, it will open a browser window for Google OAuth consent. Warn them in advance:

> First run only: a browser will open for Google OAuth. Sign in with the account that owns your Search Console property and click Allow. Future runs are silent.

Report folder layout produced:

```
./SEO_CandleStick/
└── 2026-04-15/
    ├── candlestick-data.json
    └── candlestick-report.html
```

Running again on a different day produces a new dated folder alongside — no overwrites, easy to compare reports over time.

---

## Stage 4: Open and summarise

```bash
open "$REPORT_DIR/candlestick-report.html"
```

Summarise findings in this structure:

**Improving** — keywords with green candles moving up. List the strongest movers with position ranges.

**High variance / Google testing** — keywords with wide wicks. Google is experimenting with placement — opportunity.

**Declining or stuck** — keywords that regressed or flatlined. Flag drop-offs.

**Action items** — 2 to 3 concrete next steps based on patterns.

To generate the summary without loading the full JSON into context, use a small Python one-liner via Bash that reads the JSON on disk and prints only aggregate stats (first-month vs latest-month average position per keyword). Do not cat the JSON.

---

## Notes

- `fetch_gsc_data.py` and `generate_candlestick_report.py` are pure Python. Dependencies for the fetcher: `google-auth google-auth-oauthlib google-api-python-client pyyaml`. The renderer uses stdlib only.
- HTML report is fully self-contained (inline CSS, SVG charts, no CDN). Can be emailed, archived, opened offline.
- Position scale is inverted: position 1 at the top.
- Months with no data are skipped.
- Hover any candle for detailed metrics.
- Keywords with under 2 months of data show "NEW".
- Token at `~/.config/gsc-candlestick/token.json` is created on first run and reused silently after.
- The script also honours `~/Library/Application Support/mcp-gsc/token.json` so existing `mcp-gsc` users don't need to re-auth.
