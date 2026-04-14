# GSC Candlestick SEO Report

A Claude Code skill that turns your Google Search Console data into monthly candlestick charts. See keyword ranking direction AND volatility at a glance.

## Why candlesticks for SEO

A single "average position" number lies. Daily rankings fluctuate across devices and locations, so averages hide the real story.

Candlesticks per keyword per month show:

- **Body (open to close):** did the keyword improve or decline?
- **Wicks (high to low):** how volatile? Long wicks = Google is testing placement
- **Green candle:** position improved. **Red candle:** declined
- **Goal:** push candles up AND make them thinner (stable top positions)

---

# How to install

There are two ways: let Claude do it (easier) or follow the manual steps yourself. Both end at the same place.

## Easy path: let Claude install it for you

1. Install [Claude Code](https://claude.com/claude-code) if you do not have it
2. Open Claude Code in any folder (e.g. `cd ~ && claude`)
3. Paste this prompt:

> Read this README at https://github.com/garethdouble/gsc-candlestick-report and walk me through installing the skill from scratch. Treat me as a fresh install - assume I have nothing set up and check each step. Stop and wait for me at every browser action you need me to do.

Claude will work through the 4 stages below with you, pausing at every browser step. Reply "done" when you finish each one.

---

## Manual install: the 4 stages

You only do this ONCE. After install, you can generate reports for any project in seconds.

### Stage 1: Make sure you have Python and uv

You need:
- **Python 3.11 or higher** - check with `python3 --version`. Get it at [python.org/downloads](https://www.python.org/downloads/)
- **uv** (provides the `uvx` command) - check with `which uvx`. If missing:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new terminal tab so PATH refreshes.

### Stage 2: Set up Google Cloud + Search Console API

Google requires you to identify yourself before using their API. This is a one-time setup that takes ~5 minutes.

#### 2.1 Create a Google Cloud project

Go to https://console.cloud.google.com/projectcreate

- Project name: `GSC Candlestick` (or anything memorable)
- Click **CREATE**
- Wait 10-30 seconds for it to finish
- **Confirm the new project is selected** in the top-left dropdown

#### 2.2 Enable the Search Console API

Go to https://console.cloud.google.com/apis/library/searchconsole.googleapis.com

- Confirm your new project is selected in the top-left
- Click **ENABLE**
- Wait for the green checkmark

#### 2.3 Configure the OAuth consent screen

Go to https://console.cloud.google.com/apis/credentials/consent

- User Type: select **External**, click **CREATE**
- App name: `GSC Candlestick`
- User support email: pick your email
- Developer contact: pick your email
- Click **SAVE AND CONTINUE** through Scopes screen (no changes)
- On the **Test users** screen, click **ADD USERS** and add your own Google account email. **This is required** - without it, OAuth will fail
- Click **SAVE AND CONTINUE**, then **BACK TO DASHBOARD**

#### 2.4 Create OAuth credentials and download the JSON

Go to https://console.cloud.google.com/apis/credentials

- Click **CREATE CREDENTIALS** at the top
- Select **OAuth client ID**
- Application type: **Desktop app**
- Name: `GSC Candlestick Local`
- Click **CREATE**
- A popup appears - click **DOWNLOAD JSON**
- Save the file somewhere you will remember:

```bash
mkdir -p ~/Documents/gsc-secrets
mv ~/Downloads/client_secret_*.json ~/Documents/gsc-secrets/client_secret.json
```

You now have a `client_secret.json` file. **Note its full path** - you need it in Stage 3.

### Stage 3: Connect the GSC MCP server to Claude Code

Open or create `~/.claude/settings.json` and add the GSC MCP entry:

```json
{
  "mcpServers": {
    "gsc": {
      "command": "uvx",
      "args": ["mcp-gsc"],
      "env": {
        "GOOGLE_CLIENT_SECRETS_FILE": "/Users/yourname/Documents/gsc-secrets/client_secret.json"
      }
    }
  }
}
```

Replace the path with the full path to YOUR `client_secret.json`.

If the file already has other MCP servers, just add the `gsc` entry inside the existing `mcpServers` object - do not delete anything.

### Stage 4: Install this skill

```bash
git clone https://github.com/garethdouble/gsc-candlestick-report \
  ~/.claude/skills/gsc-candlestick-report
```

### Stage 5: Restart Claude Code

1. Quit Claude Code completely (Cmd+Q on Mac, close all windows on Windows)
2. Reopen it
3. Run `/mcp` and confirm `gsc` shows as connected
4. The first time you call a GSC tool, your browser will open asking you to sign in to Google and grant Search Console access. Approve it.

You are now installed forever. Move on to "How to use it" below.

---

# How to use it

After install, generating a report on any site takes ~30 seconds.

### Option A: You already have keywords

1. `cd` to your project folder (or pick one - if you do not have one, the skill will offer to create `~/Documents/seo-reports/<sitename>` for you)
2. Copy the example config:

```bash
cp ~/.claude/skills/gsc-candlestick-report/keywords.example.yml keywords.yml
```

3. Edit `keywords.yml` - add your site URL and target keywords
4. In Claude Code, run:

```
/gsc-candlestick-report
```

### Option B: Let Claude help you build the keyword list

If you do not know what keywords to track, just run `/gsc-candlestick-report` in any folder. The skill will:

1. Detect there is no `keywords.yml`
2. Ask you about your business, services, location, competitors
3. Suggest a starter keyword list
4. Write `keywords.yml` for you
5. Pull the data and generate the report

You spend ~2 minutes answering questions. Claude does the rest.

---

# Configuration reference

Drop a `keywords.yml` into any project folder. Two formats supported:

### Flat list

```yaml
site_url: sc-domain:example.co.nz
months: 6
keywords:
  - drain unblockers auckland
  - blocked drain
  - hydro jetting
```

### Tiered (better for bigger lists)

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

### site_url format

Use the exact string Search Console shows:

- Domain property: `sc-domain:example.co.nz`
- URL-prefix property: `https://www.example.co.nz/`

If unsure, just put a placeholder. The skill will list your verified properties and let you pick.

### months

How many months of history to pull. Default `6`. Max `16` (Google's limit on Search Console data retention).

---

# Troubleshooting

### "MCP not connected" or "tool not found"

Your `~/.claude/settings.json` is missing the `gsc` entry, OR Claude Code has not been restarted since you added it. Run `/mcp` in Claude Code to confirm. If `gsc` is missing, recheck Stage 3.

### Browser does not open on first GSC call

The first call to any GSC tool should open a browser window. If it does not, check the terminal for an OAuth URL and paste it manually.

### "access_denied" or "this app is not verified"

You are signed into a Google account that is not in the **Test users** list from Stage 2.3. Either:
- Sign in with the email you added as a test user, or
- Go back to https://console.cloud.google.com/apis/credentials/consent and add your account

### "No data returned for keyword X"

The keyword gets fewer than 5 impressions per day in GSC. Try a broader term or accept the keyword will appear with no candle.

### "Quota exceeded"

You hit Google's per-minute API quota (1200 calls/minute). Wait 60 seconds and rerun. Unlikely with normal use.

---

# How it works

```
your-project/
├── keywords.yml              ← you fill this in
├── candlestick-data.json     ← skill generates (raw GSC data)
└── candlestick-report.html   ← skill generates (the report you open)
```

The skill itself lives at `~/.claude/skills/gsc-candlestick-report/`:

- `SKILL.md` - the instructions Claude follows when you run `/gsc-candlestick-report`
- `scripts/generate_candlestick_report.py` - pure Python, zero dependencies, renders the HTML
- `keywords.example.yml` - the template you copy

The HTML output is self-contained. No CDN, no JavaScript frameworks. You can email it, archive it, or open it offline.

---

# License

MIT. See [LICENSE](LICENSE).

# Credits

Built by Gareth Klapproth at [Double](https://double.nz) - a performance-led digital agency in NZ and AU.

If this saved you time, a star on the repo or a shout-out on LinkedIn ([@garethklapproth](https://www.linkedin.com/in/garethklapproth)) is always appreciated.
