# 🛡 Fraud Watch Dashboard

An end-to-end fraud monitoring dashboard for fintech risk teams — built with Python, Chart.js, and synthetic transaction data.

## What's included

| File | Description |
|------|-------------|
| `fraud_watch_dashboard.html` | **Self-contained interactive dashboard** — open in any browser |
| `fraud_gen.py` | Python script that generates the 150,400-row synthetic dataset |
| `FraudWatch_Business_Brief.docx` | Manager-friendly business brief (8 pages) |

## Dashboard pages

- **Overview** — KPI cards, 30-day time series, fraud-rate trend, channel/segment bar charts, alert summary table
- **Channels** — Fraud rate & volume per channel, daily stacked trend, sortable summary table
- **Geography** — Country-level fraud count & rate charts, top-20 region hotspot table with case drill-down
- **Segments** — Cohort trends, merchant category heatmap, segment KPI table
- **Alerts** — 5 active Critical alerts; click any card to open a **Case View modal** with the top 30 high-risk transactions

## Injected fraud scenarios

1. **Mobile card-testing (Romania, Jun 8–10)** — ~2,800 micro-transactions ($1–$15) via mobile app
2. **High-value web fraud (UK/Germany, Jun 16–20)** — ~1,400 transactions averaging $1,800+ on luxury/electronics
3. **New-customer call-center wave (Nigeria/Brazil/India, Jun 22–26)** — ~1,200 call-center fraud events targeting crypto exchanges

## Data model

`transaction_id · customer_id · timestamp · amount · channel · country · region · merchant_category · device_type · risk_score · is_fraud_flag · customer_segment`

## Quick start

```bash
pip install pandas numpy
python fraud_gen.py          # regenerates fraud_data_clean.json
# then open fraud_watch_dashboard.html in a browser
```

## Stack

- **Data**: Python · pandas · numpy
- **Dashboard**: Vanilla JS · Chart.js 4.4
- **Docs**: docx-js

## License

MIT
