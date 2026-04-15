#!/usr/bin/env python3
"""Fetch daily GSC keyword data directly via the Search Console API.

Bypasses the MCP layer — data goes straight from Google to disk, so it does
not pass through the LLM's context. A 6-month pull of 30 keywords takes a
few seconds and costs ~1k tokens instead of ~200k.

Usage:
    fetch_gsc_data.py <keywords.yml> <output.json> [--months N]

Credentials resolution (first match wins):
    1. GSC_TOKEN_FILE env var
    2. ~/.config/gsc-candlestick/token.json   (preferred)
    3. ~/Library/Application Support/mcp-gsc/token.json   (existing mcp-gsc users)

If no token exists, the script looks for OAuth client secrets at:
    1. GSC_OAUTH_CLIENT_SECRETS_FILE env var
    2. ~/.config/gsc-candlestick/credentials.json
    3. ~/Documents/gsc-secrets/client_secrets.json   (mcp-gsc default)

…and runs a local-server OAuth flow on first run, saving the resulting token
to the preferred location for future use.
"""

import json
import os
import sys
import time
import threading
from pathlib import Path
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install pyyaml")

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    sys.exit(
        "Missing dependencies. Install with:\n"
        "  pip install google-auth google-auth-oauthlib google-api-python-client pyyaml"
    )

SCOPES = ["https://www.googleapis.com/auth/webmasters"]

PREFERRED_TOKEN = Path.home() / ".config/gsc-candlestick/token.json"
LEGACY_MCP_TOKEN = Path.home() / "Library/Application Support/mcp-gsc/token.json"

PREFERRED_SECRETS = Path.home() / ".config/gsc-candlestick/credentials.json"
LEGACY_MCP_SECRETS = Path.home() / "Documents/gsc-secrets/client_secrets.json"


def find_token_path():
    env = os.environ.get("GSC_TOKEN_FILE")
    if env:
        return Path(env)
    for p in (PREFERRED_TOKEN, LEGACY_MCP_TOKEN):
        if p.exists():
            return p
    return PREFERRED_TOKEN


def find_secrets_path():
    env = os.environ.get("GSC_OAUTH_CLIENT_SECRETS_FILE")
    if env:
        return Path(env)
    for p in (PREFERRED_SECRETS, LEGACY_MCP_SECRETS):
        if p.exists():
            return p
    return None


def load_credentials():
    token_path = find_token_path()
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            return creds

    secrets = find_secrets_path()
    if not secrets:
        sys.exit(
            "\nNo GSC credentials found. Before first use you need to:\n"
            "  1. Create a Google Cloud OAuth client (Desktop app)\n"
            "  2. Download the JSON\n"
            "  3. Save it to ~/.config/gsc-candlestick/credentials.json\n\n"
            "See the skill README for step-by-step Google Cloud setup:\n"
            "  https://github.com/gareth-builds/gsc-candlestick-report#google-cloud-setup\n"
        )

    print(f"No token at {token_path}. Starting OAuth consent flow (browser will open)…")
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    PREFERRED_TOKEN.parent.mkdir(parents=True, exist_ok=True)
    PREFERRED_TOKEN.write_text(creds.to_json())
    print(f"Saved token to {PREFERRED_TOKEN}")
    return creds


_thread_local = threading.local()


def get_service(creds):
    svc = getattr(_thread_local, "service", None)
    if svc is None:
        svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        _thread_local.service = svc
    return svc


def fetch_keyword(creds, site_url, keyword, start_date, end_date, retries=3):
    """One GSC query for one keyword, grouped by date. Retries on transient errors."""
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["date"],
        "dimensionFilterGroups": [{
            "filters": [{
                "dimension": "query",
                "operator": "equals",
                "expression": keyword,
            }]
        }],
        "rowLimit": 500,
        "dataState": "all",
    }
    last_err = None
    for attempt in range(retries):
        try:
            service = get_service(creds)
            resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
            break
        except Exception as e:
            last_err = e
            _thread_local.service = None
            time.sleep(0.5 * (attempt + 1))
    else:
        raise last_err

    out = []
    for r in resp.get("rows", []):
        position = r.get("position", 0)
        impressions = r.get("impressions", 0)
        if impressions == 0 and position == 0:
            continue
        out.append({
            "date": r["keys"][0],
            "clicks": r.get("clicks", 0),
            "impressions": impressions,
            "ctr": round(r.get("ctr", 0), 5),
            "position": round(position, 2),
        })
    return out


def normalise_keywords(kw_config):
    """Accept flat list or tiered dict. Returns list of (tier, keyword)."""
    if isinstance(kw_config, list):
        return [("keywords", k) for k in kw_config]
    out = []
    for tier, kws in kw_config.items():
        for k in kws:
            out.append((tier, k))
    return out


def parse_args(argv):
    if len(argv) < 3:
        sys.exit(
            "Usage: fetch_gsc_data.py <keywords.yml> <output.json> [--months N]"
        )
    config_path = Path(argv[1])
    output_path = Path(argv[2])
    months_override = None
    for i, arg in enumerate(argv[3:], start=3):
        if arg == "--months" and i + 1 < len(argv):
            months_override = int(argv[i + 1])
    return config_path, output_path, months_override


def main():
    config_path, output_path, months_override = parse_args(sys.argv)

    config = yaml.safe_load(config_path.read_text())
    site_url = config["site_url"]
    months = months_override or config.get("months", 6)
    kw_list = normalise_keywords(config["keywords"])

    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)

    print(f"Fetching {len(kw_list)} keywords from {start_date} to {end_date}…")
    creds = load_credentials()

    results = {}
    failures = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(fetch_keyword, creds, site_url, kw, str(start_date), str(end_date)): (tier, kw)
            for tier, kw in kw_list
        }
        for fut in as_completed(futures):
            tier, kw = futures[fut]
            try:
                data = fut.result()
            except Exception as e:
                print(f"  FAIL {kw}: {e}")
                failures.append(kw)
                data = []
            results.setdefault(tier, []).append({"keyword": kw, "daily_data": data})
            print(f"  {kw}: {len(data)} rows")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "site_url": site_url,
        "report_date": str(end_date),
        "keywords": results,
    }
    output_path.write_text(json.dumps(out, separators=(",", ":")))
    total_rows = sum(len(kw["daily_data"]) for tier in results.values() for kw in tier)
    size_kb = output_path.stat().st_size / 1024
    print(f"\nWrote {output_path} — {len(kw_list)} keywords, {total_rows} rows, {size_kb:.1f} KB")
    if failures:
        print(f"  {len(failures)} failed: {', '.join(failures)}")


if __name__ == "__main__":
    main()
