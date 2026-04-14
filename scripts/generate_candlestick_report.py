#!/usr/bin/env python3
"""
Generate an HTML candlestick report for SEO keyword rankings.

Usage:
    python generate_candlestick_report.py <input.json> [output.html]

Input JSON format:
{
    "site_url": "example.co.nz",
    "report_date": "2026-04-13",
    "keywords": {
        "tier_1": [
            {
                "keyword": "drain unblockers",
                "daily_data": [
                    {"date": "2026-03-16", "clicks": 1, "impressions": 50, "ctr": 0.02, "position": 9.5}
                ]
            }
        ]
    }
}
"""

import json
import sys
from datetime import datetime
from collections import defaultdict

# Minimum impressions a daily data point must have to be included in candle calculations.
# Days below this threshold are treated as noise and excluded.
MIN_IMPRESSIONS = 5


def process_data(data):
    """Process raw daily data into monthly OHLC candles per keyword."""
    result = {}

    for tier_name, keywords in data.get("keywords", {}).items():
        result[tier_name] = []
        for kw_data in keywords:
            keyword = kw_data["keyword"]
            daily = kw_data.get("daily_data", [])

            # Filter out days below the impression threshold before grouping
            daily = [d for d in daily if d.get("impressions", 0) >= MIN_IMPRESSIONS]

            # Group by month
            monthly = defaultdict(list)
            for day in daily:
                month_key = day["date"][:7]
                monthly[month_key].append(day)

            # Calculate OHLC per month
            candles = []
            for month, days in sorted(monthly.items()):
                positions = [d["position"] for d in days if d.get("position")]
                if not positions:
                    continue

                days_sorted = sorted(days, key=lambda d: d["date"])

                candle = {
                    "month": month,
                    "open": days_sorted[0]["position"],
                    "close": days_sorted[-1]["position"],
                    "high": min(positions),       # Best position (lowest number)
                    "low": max(positions),        # Worst position (highest number)
                    "impressions": sum(d.get("impressions", 0) for d in days),
                    "clicks": sum(d.get("clicks", 0) for d in days),
                    "avg_position": sum(positions) / len(positions),
                    "variance": max(positions) - min(positions),
                    "days_counted": len(positions),
                }
                candles.append(candle)

            result[tier_name].append({"keyword": keyword, "candles": candles})

    return result


def compute_summary(processed):
    """Compute summary stats across all keywords."""
    total_keywords = 0
    page_one = 0
    improving = 0
    declining = 0
    stable = 0
    total_impressions = 0
    total_clicks = 0

    for keywords in processed.values():
        for kw in keywords:
            total_keywords += 1
            if not kw["candles"]:
                continue

            latest = kw["candles"][-1]
            total_impressions += latest["impressions"]
            total_clicks += latest["clicks"]

            if latest["close"] <= 10:
                page_one += 1

            if len(kw["candles"]) >= 2:
                prev = kw["candles"][-2]
                if latest["close"] < prev["close"] - 0.5:
                    improving += 1
                elif latest["close"] > prev["close"] + 0.5:
                    declining += 1
                else:
                    stable += 1

    return {
        "total_keywords": total_keywords,
        "page_one": page_one,
        "improving": improving,
        "declining": declining,
        "stable": stable,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
    }


def render_candlestick_chart(keyword, candles, all_months):
    """Render an SVG candlestick chart for a single keyword."""
    if not candles:
        return '<div class="no-data">No ranking data available</div>'

    chart_width = 700
    chart_height = 180
    pad_l, pad_r, pad_t, pad_b = 50, 20, 15, 30

    plot_w = chart_width - pad_l - pad_r
    plot_h = chart_height - pad_t - pad_b

    all_positions = []
    for c in candles:
        all_positions.extend([c["high"], c["low"], c["open"], c["close"]])

    min_pos = max(1, min(all_positions) - 2)
    max_pos = max(all_positions) + 2
    pos_range = max(max_pos - min_pos, 1)

    def pos_to_y(pos):
        return pad_t + ((pos - min_pos) / pos_range) * plot_h

    num_months = len(all_months)
    candle_w = min(36, (plot_w / max(num_months, 1)) * 0.55)
    candle_spacing = plot_w / max(num_months, 1)
    month_idx = {m: i for i, m in enumerate(all_months)}

    els = []

    # Grid lines
    for i in range(6):
        pos_val = min_pos + (pos_range * i / 5)
        y = pos_to_y(pos_val)
        els.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{chart_width - pad_r}" '
            f'y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>'
        )
        els.append(
            f'<text x="{pad_l - 8}" y="{y:.1f}" text-anchor="end" '
            f'dominant-baseline="middle" class="axis-label">{pos_val:.0f}</text>'
        )

    # Month labels
    for m in all_months:
        if m in month_idx:
            x = pad_l + (month_idx[m] + 0.5) * candle_spacing
            label = datetime.strptime(m, "%Y-%m").strftime("%b %y")
            els.append(
                f'<text x="{x:.1f}" y="{chart_height - 5}" text-anchor="middle" '
                f'class="axis-label">{label}</text>'
            )

    # Candles
    for candle in candles:
        if candle["month"] not in month_idx:
            continue

        idx = month_idx[candle["month"]]
        xc = pad_l + (idx + 0.5) * candle_spacing
        xl = xc - candle_w / 2

        y_high = pos_to_y(candle["high"])
        y_low = pos_to_y(candle["low"])
        y_open = pos_to_y(candle["open"])
        y_close = pos_to_y(candle["close"])

        is_green = candle["close"] <= candle["open"]
        color = "#22c55e" if is_green else "#ef4444"

        body_top = min(y_open, y_close)
        body_h = max(abs(y_close - y_open), 3)

        # Wick
        els.append(
            f'<line x1="{xc:.1f}" y1="{y_high:.1f}" x2="{xc:.1f}" '
            f'y2="{y_low:.1f}" stroke="{color}" stroke-width="1.5"/>'
        )

        # Body with data attributes for custom tooltip
        ctr = (
            (candle["clicks"] / candle["impressions"] * 100)
            if candle["impressions"] > 0
            else 0
        )

        els.append(
            f'<rect x="{xl:.1f}" y="{body_top:.1f}" width="{candle_w:.1f}" '
            f'height="{body_h:.1f}" fill="{color}" rx="2" class="candle" '
            f'data-month="{candle["month"]}" '
            f'data-open="{candle["open"]:.1f}" data-close="{candle["close"]:.1f}" '
            f'data-high="{candle["high"]:.1f}" data-low="{candle["low"]:.1f}" '
            f'data-imp="{candle["impressions"]}" data-clicks="{candle["clicks"]}" '
            f'data-ctr="{ctr:.2f}" data-variance="{candle["variance"]:.1f}" '
            f'/>'
        )

    svg = "\n".join(els)
    return (
        f'<svg class="chart" viewBox="0 0 {chart_width} {chart_height}" '
        f'preserveAspectRatio="xMidYMid meet">{svg}</svg>'
    )


def build_movers(processed):
    """Find keywords with biggest position changes in the latest month vs previous."""
    movers = []
    for keywords in processed.values():
        for kw in keywords:
            if len(kw["candles"]) < 2:
                continue
            prev = kw["candles"][-2]
            latest = kw["candles"][-1]
            change = prev["close"] - latest["close"]  # Positive = improved
            movers.append(
                {
                    "keyword": kw["keyword"],
                    "prev_pos": prev["close"],
                    "curr_pos": latest["close"],
                    "change": change,
                }
            )

    movers.sort(key=lambda m: m["change"], reverse=True)
    improved = [m for m in movers if m["change"] > 1][:5]
    declined = [m for m in movers if m["change"] < -1]
    declined.sort(key=lambda m: m["change"])
    declined = declined[:5]
    return improved, declined


def generate_html(raw_data, processed):
    """Generate the full standalone HTML report."""
    site_url = raw_data.get("site_url", "Unknown")
    report_date = raw_data.get("report_date", datetime.now().strftime("%Y-%m-%d"))

    all_months = set()
    for tier_kws in processed.values():
        for kw in tier_kws:
            for c in kw["candles"]:
                all_months.add(c["month"])
    months_sorted = sorted(all_months)

    date_range = (
        f'{months_sorted[0]} to {months_sorted[-1]}' if months_sorted else "No data"
    )

    summary = compute_summary(processed)
    improved, declined = build_movers(processed)

    # Summary cards
    summary_html = f"""
    <div class="summary-grid">
        <div class="card">
            <div class="card-value">{summary['total_keywords']}</div>
            <div class="card-label">Keywords Tracked</div>
        </div>
        <div class="card accent-green">
            <div class="card-value">{summary['page_one']}</div>
            <div class="card-label">On Page 1</div>
        </div>
        <div class="card accent-green">
            <div class="card-value">{summary['improving']}</div>
            <div class="card-label">Improving</div>
        </div>
        <div class="card accent-red">
            <div class="card-value">{summary['declining']}</div>
            <div class="card-label">Declining</div>
        </div>
        <div class="card">
            <div class="card-value">{summary['stable']}</div>
            <div class="card-label">Stable</div>
        </div>
        <div class="card">
            <div class="card-value">{summary['total_impressions']:,}</div>
            <div class="card-label">Impressions (latest month)</div>
        </div>
        <div class="card">
            <div class="card-value">{summary['total_clicks']}</div>
            <div class="card-label">Clicks (latest month)</div>
        </div>
    </div>
    """

    # Movers section
    movers_html = ""
    if improved or declined:
        movers_html = '<div class="movers-section"><h2>Biggest Movers (Latest Month)</h2><div class="movers-grid">'
        if improved:
            movers_html += '<div class="movers-col"><h3 class="green">Improved</h3>'
            for m in improved:
                movers_html += (
                    f'<div class="mover-row green">'
                    f'<span class="mover-kw">{m["keyword"]}</span>'
                    f'<span class="mover-change">+{m["change"]:.1f} positions</span>'
                    f'<span class="mover-pos">{m["prev_pos"]:.1f} &rarr; {m["curr_pos"]:.1f}</span>'
                    f"</div>"
                )
            movers_html += "</div>"
        if declined:
            movers_html += '<div class="movers-col"><h3 class="red">Declined</h3>'
            for m in declined:
                movers_html += (
                    f'<div class="mover-row red">'
                    f'<span class="mover-kw">{m["keyword"]}</span>'
                    f'<span class="mover-change">{m["change"]:.1f} positions</span>'
                    f'<span class="mover-pos">{m["prev_pos"]:.1f} &rarr; {m["curr_pos"]:.1f}</span>'
                    f"</div>"
                )
            movers_html += "</div>"
        movers_html += "</div></div>"

    # Keyword tier sections
    sections_html = ""
    for tier_name, keywords in processed.items():
        tier_label = tier_name.replace("_", " ").title().replace("Tier ", "Tier ")
        sections_html += f'<div class="tier-section"><h2>{tier_label}</h2>'

        for kw in keywords:
            chart_svg = render_candlestick_chart(
                kw["keyword"], kw["candles"], months_sorted
            )

            latest = kw["candles"][-1] if kw["candles"] else None
            metrics_html = ""
            if latest:
                ctr = (
                    (latest["clicks"] / latest["impressions"] * 100)
                    if latest["impressions"] > 0
                    else 0
                )
                if len(kw["candles"]) >= 2:
                    prev = kw["candles"][-2]
                    if latest["close"] < prev["close"] - 0.5:
                        direction = "improving"
                    elif latest["close"] > prev["close"] + 0.5:
                        direction = "declining"
                    else:
                        direction = "stable"
                else:
                    direction = "new"

                dir_symbols = {
                    "improving": "&#9650; IMPROVING",
                    "declining": "&#9660; DECLINING",
                    "stable": "&#9644; STABLE",
                    "new": "&#9733; NEW",
                }

                metrics_html = f"""
                <div class="kw-metrics">
                    <span class="metric">Position: <strong>{latest['close']:.1f}</strong></span>
                    <span class="metric">Impressions: <strong>{latest['impressions']:,}</strong></span>
                    <span class="metric">Clicks: <strong>{latest['clicks']}</strong></span>
                    <span class="metric">CTR: <strong>{ctr:.2f}%</strong></span>
                    <span class="metric">Variance: <strong>{latest['variance']:.1f}</strong></span>
                    <span class="metric dir-{direction}">{dir_symbols[direction]}</span>
                </div>"""

            sections_html += f"""
            <div class="kw-block">
                <h3>{kw['keyword']}</h3>
                {chart_svg}
                {metrics_html}
            </div>"""

        sections_html += "</div>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SEO Candlestick Report - {site_url}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f8fafc;color:#1e293b;line-height:1.6}}
.container{{max-width:920px;margin:0 auto;padding:40px 20px}}

header{{text-align:center;margin-bottom:40px;padding-bottom:30px;border-bottom:1px solid #e2e8f0}}
h1{{font-size:1.8rem;font-weight:700;color:#0f172a;margin-bottom:6px;letter-spacing:-0.02em}}
.subtitle{{font-size:1.05rem;color:#475569}}
.date-range{{font-size:.85rem;color:#94a3b8;margin-top:4px}}

.summary-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px;margin-bottom:36px}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px;text-align:center;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.card-value{{font-size:1.6rem;font-weight:700;color:#0f172a}}
.card-label{{font-size:.75rem;color:#64748b;margin-top:2px;text-transform:uppercase;letter-spacing:.05em}}
.card.accent-green .card-value{{color:#16a34a}}
.card.accent-red .card-value{{color:#dc2626}}

.movers-section{{margin-bottom:36px}}
.movers-section h2{{font-size:1.1rem;color:#475569;margin-bottom:14px;text-transform:uppercase;letter-spacing:.05em}}
.movers-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.movers-col h3{{font-size:.9rem;margin-bottom:8px}}
.movers-col h3.green{{color:#16a34a}}
.movers-col h3.red{{color:#dc2626}}
.mover-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#fff;border:1px solid #e2e8f0;border-radius:6px;margin-bottom:6px;font-size:.85rem}}
.mover-row.green{{border-left:3px solid #16a34a}}
.mover-row.red{{border-left:3px solid #dc2626}}
.mover-kw{{color:#1e293b;font-weight:500;flex:1}}
.mover-change{{color:#64748b;margin:0 12px;white-space:nowrap}}
.mover-row.green .mover-change{{color:#16a34a}}
.mover-row.red .mover-change{{color:#dc2626}}
.mover-pos{{color:#94a3b8;font-size:.8rem;white-space:nowrap}}

.legend{{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:20px;margin-bottom:36px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.legend h3{{font-size:.85rem;color:#64748b;margin-bottom:10px;text-transform:uppercase;letter-spacing:.05em}}
.legend-items{{display:flex;gap:20px;flex-wrap:wrap}}
.legend-item{{display:flex;align-items:center;gap:8px;font-size:.82rem;color:#475569}}
.legend-note{{margin-top:10px;font-size:.78rem;color:#94a3b8;font-style:italic}}

.tier-section{{margin-bottom:48px}}
.tier-section>h2{{font-size:1.2rem;color:#0f172a;margin-bottom:16px;padding-bottom:8px;border-bottom:2px solid #3b82f6}}

.kw-block{{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px 20px;margin-bottom:12px;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.kw-block h3{{font-size:.95rem;color:#334155;margin-bottom:10px;font-weight:600}}
.chart{{width:100%;max-height:180px}}
.axis-label{{font-size:10px;fill:#94a3b8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}}
.candle{{cursor:pointer;transition:opacity .15s}}
.candle:hover{{opacity:.75;stroke:#0f172a;stroke-width:1}}

.kw-metrics{{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;padding-top:10px;border-top:1px solid #e2e8f0}}
.metric{{font-size:.8rem;color:#64748b}}
.metric strong{{color:#1e293b}}
.dir-improving{{color:#16a34a;font-weight:600;font-size:.8rem}}
.dir-declining{{color:#dc2626;font-weight:600;font-size:.8rem}}
.dir-stable{{color:#ca8a04;font-weight:600;font-size:.8rem}}
.dir-new{{color:#2563eb;font-weight:600;font-size:.8rem}}

.no-data{{padding:16px;text-align:center;color:#94a3b8;font-style:italic;font-size:.85rem}}

footer{{text-align:center;margin-top:60px;padding-top:20px;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:.8rem}}

#tooltip{{position:fixed;display:none;background:#0f172a;color:#f1f5f9;border-radius:8px;padding:12px 16px;font-size:.8rem;line-height:1.5;pointer-events:none;z-index:1000;box-shadow:0 4px 12px rgba(0,0,0,.15);max-width:280px}}
#tooltip .tt-month{{font-weight:700;font-size:.9rem;margin-bottom:6px;color:#fff}}
#tooltip .tt-row{{display:flex;justify-content:space-between;gap:16px}}
#tooltip .tt-label{{color:#94a3b8}}
#tooltip .tt-val{{font-weight:600;color:#f1f5f9}}
#tooltip .tt-val.best{{color:#4ade80}}
#tooltip .tt-val.worst{{color:#f87171}}
#tooltip .tt-divider{{border-top:1px solid #334155;margin:6px 0}}

@media(max-width:768px){{
    .summary-grid{{grid-template-columns:repeat(3,1fr)}}
    .movers-grid{{grid-template-columns:1fr}}
    .kw-metrics{{flex-direction:column;gap:6px}}
    .legend-items{{flex-direction:column}}
}}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>SEO Candlestick Report</h1>
        <div class="subtitle">{site_url}</div>
        <div class="date-range">{date_range} | Generated {report_date}</div>
    </header>

    {summary_html}

    {movers_html}

    <div class="legend">
        <h3>How to Read the Charts</h3>
        <div class="legend-items">
            <div class="legend-item">
                <svg width="24" height="40"><line x1="12" y1="4" x2="12" y2="36" stroke="#94a3b8" stroke-width="1"/><rect x="6" y="12" width="12" height="16" fill="#22c55e" rx="2"/></svg>
                <span><strong>Green:</strong> position improved (close better than open)</span>
            </div>
            <div class="legend-item">
                <svg width="24" height="40"><line x1="12" y1="4" x2="12" y2="36" stroke="#94a3b8" stroke-width="1"/><rect x="6" y="12" width="12" height="16" fill="#ef4444" rx="2"/></svg>
                <span><strong>Red:</strong> position declined (close worse than open)</span>
            </div>
            <div class="legend-item">
                <svg width="24" height="6"><line x1="0" y1="3" x2="24" y2="3" stroke="#94a3b8" stroke-width="1.5"/></svg>
                <span><strong>Wicks:</strong> best and worst position that month (longer = more variance)</span>
            </div>
        </div>
        <p class="legend-note">Position 1 is at the top of each chart. The goal: move candles up and make them thinner.</p>
    </div>

    {sections_html}

    <footer>
        <p>Generated by Double | Candlestick SEO Methodology</p>
    </footer>
</div>
<div id="tooltip"></div>
<script>
(function(){{
    var tt = document.getElementById('tooltip');
    document.querySelectorAll('.candle').forEach(function(el){{
        el.addEventListener('mouseenter', function(e){{
            var d = this.dataset;
            var months = {{'01':'Jan','02':'Feb','03':'Mar','04':'Apr','05':'May','06':'Jun','07':'Jul','08':'Aug','09':'Sep','10':'Oct','11':'Nov','12':'Dec'}};
            var parts = d.month.split('-');
            var label = months[parts[1]] + ' ' + parts[0];
            tt.innerHTML = '<div class="tt-month">' + label + '</div>' +
                '<div class="tt-row"><span class="tt-label">Best position</span><span class="tt-val best">' + d.high + '</span></div>' +
                '<div class="tt-row"><span class="tt-label">Worst position</span><span class="tt-val worst">' + d.low + '</span></div>' +
                '<div class="tt-row"><span class="tt-label">Open</span><span class="tt-val">' + d.open + '</span></div>' +
                '<div class="tt-row"><span class="tt-label">Close</span><span class="tt-val">' + d.close + '</span></div>' +
                '<div class="tt-divider"></div>' +
                '<div class="tt-row"><span class="tt-label">Impressions</span><span class="tt-val">' + Number(d.imp).toLocaleString() + '</span></div>' +
                '<div class="tt-row"><span class="tt-label">Clicks</span><span class="tt-val">' + d.clicks + '</span></div>' +
                '<div class="tt-row"><span class="tt-label">CTR</span><span class="tt-val">' + d.ctr + '%</span></div>' +
                '<div class="tt-row"><span class="tt-label">Variance</span><span class="tt-val">' + d.variance + '</span></div>';
            tt.style.display = 'block';
        }});
        el.addEventListener('mousemove', function(e){{
            var x = e.clientX + 16;
            var y = e.clientY - 10;
            if (x + 280 > window.innerWidth) x = e.clientX - 296;
            if (y + tt.offsetHeight > window.innerHeight) y = window.innerHeight - tt.offsetHeight - 8;
            tt.style.left = x + 'px';
            tt.style.top = y + 'px';
        }});
        el.addEventListener('mouseleave', function(){{
            tt.style.display = 'none';
        }});
    }});
}})();
</script>
</body>
</html>"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_candlestick_report.py <input.json> [output.html]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "candlestick-report.html"

    with open(input_file) as f:
        data = json.load(f)

    processed = process_data(data)
    html = generate_html(data, processed)

    with open(output_file, "w") as f:
        f.write(html)

    print(f"Report saved to {output_file}")


if __name__ == "__main__":
    main()
