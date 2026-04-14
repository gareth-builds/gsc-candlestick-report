# GSC Candlestick SEO Report

A Claude Code skill that turns your Google Search Console data into monthly candlestick charts. See direction AND volatility of your keyword rankings at a glance.

## Why candlesticks for SEO

A single "average position" number is misleading. Daily rankings fluctuate across devices and locations, so averaging them hides the real story.

Candlesticks show the full picture per month:

- **Body (open to close):** Did the keyword improve or decline that month?
- **Wicks (high to low):** How volatile was it? Long wicks = Google is testing.
- **Green candle:** Position improved (close is better than open)
- **Red candle:** Position declined
- **Goal:** Push candles up AND make them thinner (stable top positions)

## Requirements

You need all four before this skill will work:

1. **[Claude Code](https://claude.com/claude-code)** installed
2. **[AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc)** MCP server connected to Claude Code
3. **Google OAuth credentials** for Search Console (the mcp-gsc README walks through this)
4. **At least one Search Console property** you own

If you skip any of these, the skill will stop and tell you what is missing.

## Easiest setup: let Claude do it for you

If you are new to MCP servers or do not want to follow the manual steps below, you can hand the whole setup to Claude Code.

1. Clone this repo anywhere on your machine:

```bash
git clone https://github.com/garethdouble/gsc-candlestick-report ~/gsc-candlestick-report
```

2. Open that folder in Claude Code:

```bash
cd ~/gsc-candlestick-report
claude
```

3. Paste this prompt:

> Read the README.md in this folder. Help me:
> 1. Install the GSC MCP server (AminForou/mcp-gsc) and connect it to Claude Code
> 2. Move this skill into ~/.claude/skills/ so it loads automatically
> 3. Ask me for my website URL and the keywords I want to track
> 4. Create a keywords.yml file for me in a new project folder
> 5. Run the report once we are set up

Claude will walk you through the OAuth setup, check the MCP is connected, install the skill, and ask you for your site and keywords. You do not need to understand the internals.

## Manual install

### 1. Install the GSC MCP server

Follow the full guide at [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc).

Short version:

```bash
git clone https://github.com/AminForou/mcp-gsc ~/mcp-gsc
cd ~/mcp-gsc
# Follow the repo's setup for Google OAuth service account credentials
```

Then register it in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "gsc": {
      "command": "python",
      "args": ["-m", "mcp_gsc"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/absolute/path/to/service-account.json"
      }
    }
  }
}
```

Restart Claude Code. Run `/mcp` to confirm `gsc` shows as connected.

### 2. Install this skill

```bash
git clone https://github.com/garethdouble/gsc-candlestick-report \
  ~/.claude/skills/gsc-candlestick-report
```

Restart Claude Code. The skill is now available in every session.

## Use it

### First run on a new project

```bash
cd ~/path/to/your-project
cp ~/.claude/skills/gsc-candlestick-report/keywords.example.yml keywords.yml
```

Edit `keywords.yml` - add your site URL and the keywords you want to track:

```yaml
site_url: sc-domain:example.co.nz
months: 6
keywords:
  - your first keyword
  - your second keyword
  - your third keyword
```

Then in Claude Code:

```
/gsc-candlestick-report
```

The skill will:

1. Read your `keywords.yml`
2. Pull 6 months of daily position data from GSC (in parallel)
3. Write `candlestick-report.html` to your project directory
4. Open it in your browser
5. Summarise movers, volatility, and suggested next actions

### Tiered keyword tracking

For bigger lists, group keywords by priority:

```yaml
site_url: sc-domain:example.co.nz
months: 6
keywords:
  tier_1:
    - primary money keyword
    - another money keyword
  tier_2:
    - supporting service term
  content:
    - informational blog query
```

The report sections mirror your tiers.

## Configuration reference

| Key | Required | Default | Notes |
|-----|----------|---------|-------|
| `site_url` | Yes | - | Use exact format from Search Console. Domain property: `sc-domain:example.co.nz`. URL-prefix: `https://www.example.co.nz/` |
| `months` | No | 6 | How many months of history to pull |
| `keywords` | Yes | - | Flat list OR dict of tiers |

## Troubleshooting

**"mcp__gsc__get_advanced_search_analytics not found"**
The GSC MCP is not connected. Go back to the install step and verify `/mcp` shows `gsc` as connected.

**"No data returned for keyword X"**
The keyword gets fewer than 5 impressions per day. Try a broader term, or accept that it will appear with no candle.

**"site_url not recognised"**
Use the exact format GSC shows you. For domain properties the prefix `sc-domain:` is required.

**Report is empty / no candles render**
Check `candlestick-data.json` in your project directory. If `daily_data` arrays are empty, GSC has no data for those queries in the window. Try widening `months`.

## How it works

```
your-project/
├── keywords.yml              ← you fill this in
├── candlestick-data.json     ← skill generates (raw GSC data)
└── candlestick-report.html   ← skill generates (the report you open)
```

The skill itself lives at `~/.claude/skills/gsc-candlestick-report/`. It contains:

- `SKILL.md` - the instructions Claude Code follows
- `scripts/generate_candlestick_report.py` - pure Python, zero dependencies, renders the HTML
- `keywords.example.yml` - the template you copy into each project

The HTML output is self-contained. No CDN, no JavaScript frameworks. You can email it, archive it, or open it offline.

## License

MIT. See [LICENSE](LICENSE).

## Credits

Built by Gareth Klapproth at [Double](https://double.nz) - a performance-led digital agency in NZ and AU.

If this saved you time, a star on the repo or a shout-out on LinkedIn ([@garethklapproth](https://www.linkedin.com/in/garethklapproth)) is always appreciated.
