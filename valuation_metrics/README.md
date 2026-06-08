# valuation_metrics

Compute valuation metrics for a stock ticker on a given date, using **only free
data sources** (no API keys, no paid accounts).

## Metrics produced

- Trailing P/E
- Forward P/E
- PEG ratio
- Price / Free Cash Flow
- EV / EBITDA (forward)
- Revenue growth rate vs. valuation multiple
- Free cash flow margin

(plus market cap, enterprise value, and the raw OHLCV price record)

## Data sources

| Data | Source | Key? |
|------|--------|------|
| Daily OHLCV prices | [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo) | none |
| Trailing fundamentals (revenue, EBITDA, EPS, OCF, capex, debt, cash, shares) | [SEC EDGAR companyfacts](https://www.sec.gov/edgar/sec-api-documentation) | none |
| Forward estimates (fwd EPS, fwd EBITDA, growth) | [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo) | none |

## Rate limits & etiquette

- **SEC EDGAR** — hard ceiling 10 req/s per IP; this package self-throttles to
  **8 req/s** and sends a descriptive `User-Agent` (required, or SEC returns 403).
  Set your own via the `EDGAR_USER_AGENT` env var. Fundamentals are cached, so
  EDGAR is hit at most once per ticker per quarter.
- **yfinance** — used for both prices and forward estimates. It's an unofficial
  scraper; Yahoo throttles aggressively and can temporarily block your IP.
  Everything is cached (prices per ticker/date-range, estimates daily) so repeat
  runs make few or zero network calls.
- **Stooq** — dropped. Its CSV endpoint is now behind a JavaScript anti-bot
  challenge that plain HTTP clients can't pass.

## Caching

All fetched data is cached as CSV in `cache/` (git-ignored). Past-date prices and
fundamentals never change, so re-runs are instant and limit-free. Delete files in
`cache/` to force a refresh.

## Install

**Requires Python 3.11+.** Current pandas/yfinance use syntax that fails at
runtime on Python 3.8 (which is end-of-life). Check with `python3.12 --version`;
install via `brew install python@3.12` if needed.

Use a virtual environment so this project's dependencies (it upgrades numpy,
pandas, etc.) don't disturb your system or Anaconda base environment:

```bash
# 1. Create an isolated environment in the project folder (use a modern Python)
python3.12 -m venv .venv

# 2. Activate it
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows (PowerShell)

# 3. Install dependencies into the environment
pip install -r requirements.txt
```

Run all scripts and tests with the environment active. When finished, run
`deactivate` to exit it. `.venv/` is already git-ignored.

> Skipping the venv and running a bare `pip install -r requirements.txt` will
> install into whatever Python is active — fine in a pinch, but it can upgrade
> shared packages (e.g. numpy) and break other tools in that environment.

## Required setup: EDGAR contact email

SEC EDGAR requires a contact email in the request `User-Agent` (it returns a 403
otherwise). This is read from the `EDGAR_USER_AGENT` environment variable — no
email is hardcoded in the source, so nothing personal ends up in git. EDGAR
calls raise a clear error until you set it.

```bash
# one-off (current shell only) — use your own email; never hardcode it in a file
export EDGAR_USER_AGENT="shakeout-breakout you@example.com"
```

To make it permanent, add that line to your `~/.zshrc` (or `~/.bashrc`), or put
it in a `.env` file (already git-ignored) and source it before running:

```bash
echo 'export EDGAR_USER_AGENT="shakeout-breakout you@example.com"' >> ~/.zshrc
source ~/.zshrc
```

## Usage

```bash
python main.py AAPL 2026-05-01      # metrics as of a date
python main.py MSFT                 # defaults to today
python main.py NVDA 2026-05-01 --json
```

Or from Python:

```python
from main import get_metrics
result = get_metrics("AAPL", "2026-05-01")
print(result["metrics"])
```

## Important limitations (by design, to stay free)

1. **Forward estimates are current consensus.** yfinance returns *today's*
   analyst consensus regardless of the `date` you request. For current analysis
   that's accurate; for a historical date it's a present-day proxy, not what
   consensus was on that day.
2. **EBITDA is approximated.** It is not a reported line item; we compute
   `OperatingIncome + D&A` (fallback `NetIncome + Interest + Taxes + D&A`). If
   yfinance has no forward EBITDA, EV/EBITDA falls back to a trailing EBITDA
   proxy (flagged in the output).
3. **TTM is best-effort.** Built from the 4 most recent ~quarterly filings;
   falls back to the latest annual (10-K) when clean quarters aren't available.
4. **Point-in-time fundamentals** use only filings dated on/before the requested
   date (no look-ahead bias) — this part *is* historically accurate.

## Layout

```
valuation_metrics/
├── main.py              # get_metrics(ticker, date) + CLI
├── requirements.txt
├── cache/               # git-ignored CSV cache
├── src/
│   ├── config.py        # paths, rate limits, endpoints
│   ├── cache.py         # CSV read/write + staleness
│   ├── prices.py        # Stooq OHLCV
│   ├── edgar.py         # SEC fundamentals (8 req/s, point-in-time)
│   ├── estimates.py     # yfinance forward consensus
│   └── metrics.py       # pure ratio math
└── tests/
    └── test_metrics.py  # math unit tests (no network)
```

## Tests

```bash
python -m pytest tests/ -q
```
