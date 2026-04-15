# GSC Candlestick SEO Report

A Claude Code skill that turns your Google Search Console data into monthly candlestick charts. See keyword ranking direction AND volatility at a glance.

**v2 — direct API.** The skill now calls the Google Search Console API directly, bypassing the MCP layer. A 6-month pull of 30 keywords takes ~3 seconds and uses ~600 tokens of context (the v1 MCP path used ~190,000 tokens and took 5+ minutes). Same output, 100× faster.

---

# Install (one time, ~5 minutes)

There are three steps. None are optional. All live on your machine — nothing is pushed anywhere.

### Step 1 — Install the skill + Python dependencies

```bash
git clone https://github.com/gareth-builds/gsc-candlestick-report \
  ~/.claude/skills/gsc-candlestick-report

python3 -m pip install --user \
  google-auth google-auth-oauthlib google-api-python-client pyyaml
```

If `pip` blocks because of PEP 668 ("externally-managed-environment"), use a venv or add `--break-system-packages` (pipx also works).

### Step 2 — Google Cloud OAuth setup

Google needs to know who's calling the Search Console API. You're creating a Desktop-type OAuth client tied to your own Google Cloud project. ~5 minutes, one time forever.

#### 2.1 Create a Google Cloud project

Go to https://console.cloud.google.com/projectcreate

- Project name: `GSC Candlestick`
- Click **CREATE**, wait ~20 seconds
- Confirm the new project is selected in the top-left dropdown

#### 2.2 Enable the Search Console API

Go to https://console.cloud.google.com/apis/library/searchconsole.googleapis.com

- Confirm your new project is selected
- Click **ENABLE**, wait for the green checkmark

#### 2.3 Configure the OAuth consent screen

Go to https://console.cloud.google.com/apis/credentials/consent

- User Type: **External**, click **CREATE**
- App name: `GSC Candlestick`
- User support email: your email
- Developer contact: your email
- Click **SAVE AND CONTINUE** through the Scopes screen (no changes)
- On the **Test users** screen click **ADD USERS** and add your Google account email. **This is required** — OAuth fails silently without it.
- Click **SAVE AND CONTINUE** → **BACK TO DASHBOARD**

#### 2.4 Create OAuth credentials and save the JSON

Go to https://console.cloud.google.com/apis/credentials

- Click **CREATE CREDENTIALS** → **OAuth client ID**
- Application type: **Desktop app**
- Name: `GSC Candlestick Local`
- Click **CREATE** → **DOWNLOAD JSON**
- Save it to the canonical location:

```bash
mkdir -p ~/.config/gsc-candlestick
mv ~/Downloads/client_secret_*.json ~/.config/gsc-candlestick/credentials.json
```

That's it for Google Cloud. First run of the skill will open a browser for one-time consent and save a refresh token at `~/.config/gsc-candlestick/token.json`.

> **Already using the `mcp-gsc` MCP server?** Your existing `~/Documents/gsc-secrets/client_secrets.json` and `~/Library/Application Support/mcp-gsc/token.json` are detected automatically. Skip Step 2 entirely.

### Step 3 — Define your keywords

The skill reads a `keywords.yml` file in whatever project folder you run it from. You either:

- **Let the skill build one for you.** Run the skill with no config and it will walk you through 5 questions (site, industry, services, location, competitors) and suggest 10–20 starter keywords. It writes `keywords.yml` once you approve.
- **Or write it yourself.** Copy the template:

```bash
cp ~/.claude/skills/gsc-candlestick-report/keywords.example.yml ./keywords.yml
```

Then edit. Two formats are supported:

Flat list:
```yaml
site_url: sc-domain:example.co.nz
months: 6
keywords:
  - drain unblockers auckland
  - blocked drain
  - hydro jetting
```

Tiered (better for larger lists):
```yaml
site_url: sc-domain:example.co.nz
months: 6
keywords:
  tier_1:
    - primary money keyword
  tier_2:
    - supporting service term
  content:
    - informational blog query
```

`site_url` must match what Search Console shows exactly:
- Domain property: `sc-domain:example.co.nz`
- URL-prefix property: `https://www.example.co.nz/`

Not sure? The skill can list your verified properties interactively.

---

# How to use it

After install, any report run takes a few seconds.

1. `cd` into any project folder (or let the skill create `~/Documents/seo-reports/<sitename>`)
2. Make sure `keywords.yml` exists (Step 3 above)
3. In Claude Code, run `/gsc-candlestick-report`

The skill will:
1. Confirm your keyword list
2. Pull daily GSC data for every keyword in parallel
3. Write everything to `./SEO_CandleStick/YYYY-MM-DD/`:
   - `candlestick-data.json` (raw data)
   - `candlestick-report.html` (the report)
4. Open the HTML in your browser
5. Summarise improving, high-variance, and declining keywords with action items

Each run creates its own dated folder so you build a running archive automatically — no overwrites.

---

## Why candlesticks for SEO

A single "average position" number lies. Daily rankings fluctuate across devices and locations, so averages hide the real story.

Candlesticks per keyword per month show:
- **Body (open to close):** did the keyword improve or decline?
- **Wicks (high to low):** how volatile? Long wicks = Google is testing placement
- **Green candle:** position improved. **Red candle:** declined
- **Goal:** push candles up AND make them thinner (stable top positions)

---

# Troubleshooting

### "No GSC credentials found"
You skipped Step 2 or saved the JSON in the wrong place. The skill looks at:
1. `$GSC_OAUTH_CLIENT_SECRETS_FILE` env var
2. `~/.config/gsc-candlestick/credentials.json` (preferred)
3. `~/Documents/gsc-secrets/client_secrets.json` (legacy `mcp-gsc` default)

### First-run browser never opens
The fetcher uses `google-auth-oauthlib`'s local-server flow. If your browser blocks popups, read the URL from the terminal and paste it manually.

### "access_denied" or "this app is not verified"
You're signed into a Google account that isn't in the **Test users** list from Step 2.3. Either sign in with the email you added, or return to https://console.cloud.google.com/apis/credentials/consent and add your account as a test user.

### "invalid_scope: Bad Request"
Old token file with a stale scope. Delete `~/.config/gsc-candlestick/token.json` and rerun — you'll be re-prompted for consent.

### "No data returned for keyword X"
The keyword gets few or no impressions in GSC. Try a broader term. The skill renders "NEW" or a blank card for keywords with under 2 months of data.

### "Quota exceeded"
You hit Google's 1200 calls/minute limit. Wait 60 seconds and rerun. Unlikely outside very large keyword lists.

---

# How it works

```
your-project/
├── keywords.yml                        ← you edit this
└── SEO_CandleStick/
    └── 2026-04-15/
        ├── candlestick-data.json       ← raw GSC data
        └── candlestick-report.html     ← the report you open
```

The skill itself lives at `~/.claude/skills/gsc-candlestick-report/`:

- `SKILL.md` — instructions Claude follows when you run `/gsc-candlestick-report`
- `scripts/fetch_gsc_data.py` — direct GSC API fetcher (parallel, handles OAuth)
- `scripts/generate_candlestick_report.py` — pure-stdlib HTML renderer
- `keywords.example.yml` — template

The HTML output is self-contained. No CDN, no JS frameworks. Email it, archive it, open it offline.

---

# Why direct API instead of an MCP?

The MCP version of this skill fed every GSC row through the LLM's context. For 27 keywords × 180 days that's ~4,800 rows, which Claude then had to re-emit as a Python dict literal or JSON — ~144,000 output tokens per run. Output tokens are the expensive, slow part of LLM inference, so a single report took 5+ minutes and consumed huge context.

Direct API: the Python script talks to Google, writes JSON to disk. The LLM only sees "Wrote 3,961 rows, 281 KB" — ~600 total tokens, a few seconds of wall time, and context stays clean for the actual analysis.

The trade-off: one-time Google Cloud setup instead of MCP install. Worth it.

---

# License

MIT. See [LICENSE](LICENSE).

# Credits

Built by Gareth Klapproth at [Double](https://double.nz) — a performance-led digital agency in NZ and AU.

If this saved you time, a star on the repo or a shout-out on LinkedIn ([@garethklapproth](https://www.linkedin.com/in/garethklapproth)) is appreciated.
