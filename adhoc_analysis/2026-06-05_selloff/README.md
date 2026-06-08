# 2026-06-05 Mega-Cap Tech Sell-Off

Ad-hoc analysis of the June 3 → June 5, 2026 sell-off across nine mega-cap tech
names: **NVDA, MSFT, AVGO, MU, META, GOOGL, AMZN, AAPL, TSLA**.

For each ticker it computes:

- the two-day price change (Wednesday Jun 3 close → Friday Jun 5 close)
- trailing P/E, forward P/E, and PEG on each of the two dates

and renders a chart for the blog post.

## Files

| File | What it is |
|------|------------|
| `megacap_selloff_jun2026.py` | Data script — fetches prices/fundamentals/estimates and writes the CSV |
| `megacap_selloff_jun2026.csv` | Output data (one row per ticker) |
| `make_selloff_chart.py` | Chart script — renders the PNG from the CSV |
| `megacap_selloff_jun2026_chart.png` | The chart (blog hero / thumbnail) |

Both scripts rely on the reusable `valuation_metrics` package, which lives at the
repo root (`shakeout-breakout/valuation_metrics`). The data sources are SEC EDGAR
(fundamentals), yfinance (prices + forward consensus). See that package's README
for the data-source details and caveats.

## Prerequisites

- **Python 3.11+** (3.8 will fail — see the `valuation_metrics` README).
- Dependencies installed: `pip install -r ../../valuation_metrics/requirements.txt`
  plus `matplotlib` for the chart: `pip install matplotlib`.
- SEC EDGAR contact email set (required, or EDGAR returns 403). Set this to your
  own email via the environment variable — don't hardcode it in any file:

  ```bash
  export EDGAR_USER_AGENT="shakeout-breakout you@example.com"
  ```

## Replicate

From this folder (or the repo root — paths are resolved automatically):

```bash
# 1. Generate the data
python megacap_selloff_jun2026.py

# 2. Render the chart
python make_selloff_chart.py
```

Step 1 writes `megacap_selloff_jun2026.csv`; step 2 reads that CSV and writes
`megacap_selloff_jun2026_chart.png`. Re-running either overwrites its output.

To analyze a different set of tickers or dates, edit `TICKERS`, `DATE_EARLY`,
and `DATE_LATE` near the top of `megacap_selloff_jun2026.py`.

## Notes & caveats

- **Forward estimates are current consensus.** yfinance returns today's consensus
  regardless of the date requested, so forward P/E and PEG are a present-day proxy
  for the two historical dates — fine for this snapshot, not historically exact.
- **Two-day P/E moves are price-driven.** Trailing EPS and consensus don't change
  over a two-day window with no new filing, so day-to-day P/E/PEG differences here
  reflect only the price move.
- **Caching.** Fetched data is cached under `valuation_metrics/cache/` (git-ignored).
  Past-date prices/fundamentals don't change, so re-runs are fast and avoid hitting
  rate limits. Delete the relevant `cache/*.csv` files to force a refresh.
