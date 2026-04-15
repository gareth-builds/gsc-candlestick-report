# GSC Candlestick SEO Report

A Claude Code skill that turns Google Search Console data into monthly candlestick charts. See keyword ranking direction AND volatility at a glance.

**v2 — direct API.** Calls the Search Console API directly, bypassing MCP. A 6-month pull of 30 keywords takes ~3 seconds and costs ~600 tokens (vs. ~190k tokens and 5+ minutes on v1). Same output, 100× faster.

![Why candlesticks](https://img.shields.io/badge/ranking%20variance-visible-green) ![No MCP needed](https://img.shields.io/badge/MCP-not%20required-blue) ![Python stdlib render](https://img.shields.io/badge/zero--dependency%20HTML-yes-green)

---

## TL;DR for returning users

```bash
cd your-project-folder
# if you don't have keywords.yml yet:
cp ~/.claude/skills/gsc-candlestick-report/keywords.example.yml ./keywords.yml
# then in Claude Code:
/gsc-candlestick-report
```

Report lands in `./SEO_CandleStick/YYYY-MM-DD/candlestick-report.html`.

---

## Installing for the first time

Two ways: **let Claude walk you through it** (easier) or **follow the manual steps below** (faster if you're comfortable in a terminal).

### Option A — Let Claude walk you through install

Open Claude Code and paste this prompt:

```
Read https://github.com/gareth-builds/gsc-candlestick-report/blob/main/README.md
and walk me through installing and running this skill from scratch.

Rules:
- Treat me as a fresh install. Verify each prerequisite, skip what I already have.
- For every browser action (Google Cloud Console, downloads), stop and wait for me
  to reply "done".
- Once credentials.json is saved, help me create my first keywords.yml.
- Run the skill and summarise the output.
```

Claude handles the rest. Total time: ~10 minutes.

### Option B — Manual install

Three steps. All run on your machine. Nothing is pushed anywhere.

---

### Step 1 — Install the skill + Python dependencies

Copy-paste the whole block:

```bash
# Clone the skill into Claude Code's skills folder
git clone https://github.com/gareth-builds/gsc-candlestick-report \
  ~/.claude/skills/gsc-candlestick-report

# Install the 4 Python packages the fetcher needs
python3 -m pip install --user \
  google-auth google-auth-oauthlib google-api-python-client pyyaml
```

**If pip errors with `externally-managed-environment`** (macOS Homebrew / recent Debian), use either of these:

```bash
# Option 1: install for this user only, bypass the warning
python3 -m pip install --user --break-system-packages \
  google-auth google-auth-oauthlib google-api-python-client pyyaml

# Option 2: use pipx in an isolated env (recommended for laptops)
brew install pipx 2>/dev/null || python3 -m pip install --user pipx
pipx install --include-deps google-api-python-client
pipx inject google-api-python-client google-auth-oauthlib pyyaml
```

**Verify install:**

```bash
python3 -c "import yaml, google.oauth2, googleapiclient; print('OK')"
```

Should print `OK`. If it errors, the packages didn't install where Python can find them — try `python3 -m pip install --user --break-system-packages ...`.

---

### Step 2 — Google Cloud OAuth setup (~5 min, one time forever)

You're creating a Desktop-type OAuth client tied to your own Google Cloud project. The credentials stay on your machine — you're not giving anything to this project.

> **Already using the [mcp-gsc](https://github.com/AminForou/mcp-gsc) MCP server?** Your existing `~/Documents/gsc-secrets/client_secrets.json` and `~/Library/Application Support/mcp-gsc/token.json` are reused automatically. **Skip to Step 3.**

#### 2.1 Create a Google Cloud project

Click: https://console.cloud.google.com/projectcreate

- Project name: `GSC Candlestick`
- Click **CREATE**, wait ~20 seconds
- Top-left dropdown: confirm the new project is selected

#### 2.2 Enable the Search Console API

Click: https://console.cloud.google.com/apis/library/searchconsole.googleapis.com

- Confirm project selected
- Click **ENABLE**, wait for green checkmark

#### 2.3 Configure the OAuth consent screen

Click: https://console.cloud.google.com/apis/credentials/consent

- User Type: **External** → **CREATE**
- App name: `GSC Candlestick`
- User support email: pick your email
- Developer contact: pick your email
- **SAVE AND CONTINUE** through the Scopes screen (no changes)
- On the **Test users** screen, **ADD USERS** → add your Google account email. **Required** — OAuth fails silently without it.
- **SAVE AND CONTINUE** → **BACK TO DASHBOARD**

#### 2.4 Create OAuth credentials and download the JSON

Click: https://console.cloud.google.com/apis/credentials

- **CREATE CREDENTIALS** → **OAuth client ID**
- Application type: **Desktop app**
- Name: `GSC Candlestick Local`
- **CREATE** → **DOWNLOAD JSON**

Save it to the canonical location:

```bash
# Moves the just-downloaded OAuth JSON into the location the skill expects
mkdir -p ~/.config/gsc-candlestick
mv ~/Downloads/client_secret_*.json ~/.config/gsc-candlestick/credentials.json
```

**Verify the file is in the right place:**

```bash
ls -l ~/.config/gsc-candlestick/credentials.json
```

Should show a file of ~300 bytes. If "No such file or directory", the download didn't save to `~/Downloads` — look in your browser's download history and move it manually.

That's it for Google Cloud. First run of the skill opens a browser once for consent, saves a refresh token, then all future runs are silent.

---

### Step 3 — Create `keywords.yml` in your project folder

The skill reads `keywords.yml` from whatever folder you run it in. This tells it which Search Console property and which keywords to track.

**Option 1: copy the template and edit it.**

```bash
# Run this from inside the project folder you want to report on
cp ~/.claude/skills/gsc-candlestick-report/keywords.example.yml ./keywords.yml
open -e ./keywords.yml   # macOS TextEdit; Linux: xdg-open ./keywords.yml
```

**Option 2: let Claude build one for you.** Run the skill with no `keywords.yml` and it walks you through 5 questions (site, industry, services, location, competitors) then suggests 10–20 starter keywords.

**Minimum viable `keywords.yml`:**

```yaml
site_url: sc-domain:example.co.nz
months: 6
keywords:
  - drain unblockers auckland
  - blocked drain
  - hydro jetting
```

**Tiered version (better for 20+ keywords):**

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

**`site_url` format — must match Search Console exactly:**

| Type | Format |
|------|--------|
| Domain property | `sc-domain:example.co.nz` |
| URL-prefix property | `https://www.example.co.nz/` (trailing slash matters) |

Not sure? The skill can list your verified properties and let you pick.

---

## Running the skill

From inside any project folder with a valid `keywords.yml`:

**Slash command:**
```
/gsc-candlestick-report
```

**Or natural language** (Claude auto-triggers on any of these):
- "create a candlestick chart for this site"
- "run the GSC candlestick report"
- "show me keyword ranking variance"

### What you get

```
./SEO_CandleStick/
└── 2026-04-15/
    ├── candlestick-data.json       ← raw daily GSC data
    └── candlestick-report.html     ← the report, opens in any browser
```

Each run creates a fresh dated folder. No overwrites. Build a running archive automatically.

### Example console output on a successful run

```
Fetching 27 keywords from 2025-10-15 to 2026-04-15…
  drain unblockers: 180 rows
  drain unblocking auckland: 180 rows
  emergency drain unblocking: 176 rows
  ...
Wrote ./SEO_CandleStick/2026-04-15/candlestick-data.json — 27 keywords, 3961 rows, 281.8 KB
Report saved to ./SEO_CandleStick/2026-04-15/candlestick-report.html
```

Followed by Claude's analysis summary: improving keywords, high-variance (Google-testing) keywords, declining or stuck keywords, and 2–3 action items.

---

## Why candlesticks for SEO

A single "average position" number lies. Daily rankings fluctuate across devices and locations, so averages hide the real story.

Candlesticks per keyword per month show:

| Signal | Meaning |
|--------|---------|
| **Body (open → close)** | Did the keyword improve or decline this month? |
| **Wicks (high / low)** | How volatile? Long wicks = Google is still testing placement |
| **Green candle** | Position improved |
| **Red candle** | Position declined |
| **Goal** | Push candles up AND make them thinner — stable top positions |

---

## Troubleshooting

### `No GSC credentials found`
Credentials didn't make it to a location the skill checks. The skill searches (first match wins):
1. `$GSC_OAUTH_CLIENT_SECRETS_FILE` env var
2. `~/.config/gsc-candlestick/credentials.json` (preferred)
3. `~/Documents/gsc-secrets/client_secrets.json` (legacy `mcp-gsc` default)

Fix:

```bash
ls -l ~/.config/gsc-candlestick/credentials.json
# if missing, repeat Step 2.4
```

### First-run browser never opens
The fetcher uses `google-auth-oauthlib`'s local-server flow. If your browser blocks popups, copy the OAuth URL from the terminal output and paste it into a browser manually.

### `access_denied` or "this app is not verified"
You're signed into a Google account that isn't in the **Test users** list from Step 2.3. Fix:

```
https://console.cloud.google.com/apis/credentials/consent
```

Add your account as a test user, or sign in with the email you already added.

### `invalid_scope: Bad Request`
Old token with a stale scope. Delete and re-auth:

```bash
rm ~/.config/gsc-candlestick/token.json
# rerun the skill — browser will open for fresh consent
```

### `Missing dependencies`
The Python libs aren't installed where `python3` can find them. Run:

```bash
python3 -c "import yaml, google.oauth2, googleapiclient; print('OK')"
```

If it errors, revisit Step 1. On macOS with Homebrew Python, you usually need `--break-system-packages` or a venv.

### `No data returned for keyword X`
The keyword gets few or no impressions in GSC. Try a broader term. Keywords with under 2 months of data render as "NEW" on the report.

### `Quota exceeded`
You hit Google's 1200 calls/minute limit. Wait 60 seconds and rerun. Unlikely outside very large keyword lists.

---

## How it works (under the hood)

**Your project folder:**
```
your-project/
├── keywords.yml                        ← you edit this
└── SEO_CandleStick/
    └── 2026-04-15/
        ├── candlestick-data.json       ← raw GSC data
        └── candlestick-report.html     ← the report you open
```

**The skill:** `~/.claude/skills/gsc-candlestick-report/`
- `SKILL.md` — instructions Claude follows when you run `/gsc-candlestick-report`
- `scripts/fetch_gsc_data.py` — direct GSC API fetcher (parallel, handles OAuth)
- `scripts/generate_candlestick_report.py` — pure-stdlib HTML renderer (no dependencies)
- `keywords.example.yml` — template

The HTML output is self-contained. No CDN, no JS frameworks. Email it, archive it, open it offline.

---

## Why direct API instead of an MCP?

v1 used the `mcp-gsc` MCP server, which fed every GSC row through the LLM's context. For 27 keywords × 180 days that's ~4,800 rows, which Claude had to re-emit as JSON or a Python dict — **~144,000 output tokens per run**. Output tokens are the expensive, slow part of LLM inference, so a single report took 5+ minutes.

**v2 direct API:** the Python script talks to Google, writes JSON to disk. The LLM only sees one-line status output — **~600 total tokens**, ~3 seconds wall time, and your conversation context stays clean for the actual analysis work.

Trade-off: one-time Google Cloud setup instead of MCP install. Worth it.

---

## License

MIT. See [LICENSE](LICENSE).

## Credits

Built by Gareth Klapproth at [Double](https://double.nz) — a performance-led digital agency in NZ and AU.

If this saved you time, a star on the repo or a shout-out on LinkedIn ([@garethklapproth](https://www.linkedin.com/in/garethklapproth)) is appreciated.
