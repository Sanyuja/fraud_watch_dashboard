import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import random, hashlib

np.random.seed(42)
random.seed(42)

# ── Config ──────────────────────────────────────────────────────────────────
N_BASE   = 145_000
DATE_START = datetime(2026, 5, 29)
DATE_END   = datetime(2026, 6, 28)
DAYS = (DATE_END - DATE_START).days + 1

CHANNELS   = ['mobile', 'web', 'pos', 'call_center', 'api']
COUNTRIES  = ['US', 'UK', 'DE', 'FR', 'RO', 'NG', 'BR', 'CA', 'IN', 'AU']
REGIONS_BY_COUNTRY = {
    'US': ['Northeast','Southeast','Midwest','West','Southwest'],
    'UK': ['London','Midlands','Scotland','Wales','North England'],
    'DE': ['Bavaria','Berlin','Hamburg','NRW','Saxony'],
    'FR': ['Île-de-France','Provence','Normandy','Brittany','Lyon'],
    'RO': ['Bucharest','Cluj','Timisoara','Iasi','Constanta'],
    'NG': ['Lagos','Abuja','Kano','Ibadan','Port Harcourt'],
    'BR': ['São Paulo','Rio','Minas Gerais','Bahia','Paraná'],
    'CA': ['Ontario','Quebec','BC','Alberta','Manitoba'],
    'IN': ['Mumbai','Delhi','Bangalore','Chennai','Hyderabad'],
    'AU': ['NSW','Victoria','Queensland','WA','SA'],
}
MERCHANT_CATS = ['electronics','grocery','luxury','travel','fuel',
                 'entertainment','restaurant','pharmacy','clothing','crypto_exchange']
DEVICE_TYPES  = ['ios','android','desktop','tablet','unknown']
SEGMENTS      = ['new','regular','premium','high_value','dormant']

CHANNEL_W  = [0.35, 0.30, 0.20, 0.08, 0.07]
COUNTRY_W  = [0.30, 0.15, 0.10, 0.10, 0.05, 0.05, 0.08, 0.07, 0.06, 0.04]
MERCHANT_W = [0.12, 0.18, 0.08, 0.10, 0.09, 0.10, 0.12, 0.07, 0.09, 0.05]
SEGMENT_W  = [0.20, 0.40, 0.20, 0.12, 0.08]

def rand_ts(n, start, end, weights=None):
    total_sec = int((end - start).total_seconds())
    if weights is None:
        offsets = np.random.randint(0, total_sec, n)
    else:
        offsets = np.random.choice(total_sec, n, p=weights/weights.sum())
    return [start + timedelta(seconds=int(o)) for o in offsets]

# Give slightly higher traffic during business hours
hour_w = np.array([0.5,0.4,0.3,0.3,0.4,0.6,1.0,1.4,1.6,1.7,1.8,1.8,
                   1.7,1.7,1.7,1.6,1.5,1.5,1.4,1.3,1.2,1.1,0.9,0.6])
sec_w = np.repeat(hour_w, 3600)  # 86400 seconds

# ── Base population ──────────────────────────────────────────────────────────
print("Generating base transactions…")
rows = []
customer_ids = [f"C{str(i).zfill(7)}" for i in range(1, 30001)]

for _ in range(N_BASE):
    ch = np.random.choice(CHANNELS, p=CHANNEL_W)
    co = np.random.choice(COUNTRIES, p=COUNTRY_W)
    region = random.choice(REGIONS_BY_COUNTRY[co])
    seg = np.random.choice(SEGMENTS, p=SEGMENT_W)
    mc  = np.random.choice(MERCHANT_CATS, p=MERCHANT_W)
    dev = random.choice(DEVICE_TYPES)
    cid = random.choice(customer_ids)

    # Amount by segment
    base_amt = {'new': 80, 'regular': 150, 'premium': 300,
                'high_value': 800, 'dormant': 60}[seg]
    amount = round(max(1.0, np.random.lognormal(np.log(base_amt), 0.7)), 2)

    # Base fraud rate by channel
    base_fraud = {'mobile':0.012,'web':0.018,'pos':0.005,
                  'call_center':0.022,'api':0.009}[ch]
    # Adjust by segment
    seg_mult = {'new':2.0,'regular':1.0,'premium':0.8,
                'high_value':0.6,'dormant':2.5}[seg]
    # Adjust by merchant
    mc_mult = {'electronics':1.8,'luxury':1.5,'crypto_exchange':3.0,
               'travel':1.2,'grocery':0.4,'fuel':0.5,'entertainment':0.9,
               'restaurant':0.5,'pharmacy':0.6,'clothing':1.0}[mc]

    fraud_prob = min(base_fraud * seg_mult * mc_mult, 0.40)
    is_fraud = int(np.random.random() < fraud_prob)
    risk_score = round(np.random.beta(2 if not is_fraud else 6,
                                     8 if not is_fraud else 2) * 100, 1)

    rows.append({
        'channel': ch, 'country': co, 'region': region, 'segment': seg,
        'merchant_category': mc, 'device_type': dev, 'customer_id': cid,
        'amount': amount, 'is_fraud': is_fraud, 'risk_score': risk_score,
    })

df_base = pd.DataFrame(rows)
total_sec = int((DATE_END - DATE_START).total_seconds())
df_base['timestamp'] = [DATE_START + timedelta(seconds=int(s))
                        for s in np.random.randint(0, total_sec, N_BASE)]

# ─── FRAUD SCENARIO 1: Mobile card-testing spike in Romania (days 10-12) ───
print("Injecting fraud scenario 1: mobile card-testing in Romania…")
fraud1_n = 2800
fraud1_start = DATE_START + timedelta(days=10)
fraud1_end   = DATE_START + timedelta(days=12)
f1_sec = int((fraud1_end - fraud1_start).total_seconds())
fraud1_rows = []
for _ in range(fraud1_n):
    region = random.choice(REGIONS_BY_COUNTRY['RO'])
    fraud1_rows.append({
        'timestamp': fraud1_start + timedelta(seconds=random.randint(0, f1_sec)),
        'channel': 'mobile', 'country': 'RO', 'region': region,
        'segment': np.random.choice(['new','dormant'], p=[0.7,0.3]),
        'merchant_category': np.random.choice(['electronics','clothing'], p=[0.6,0.4]),
        'device_type': random.choice(['android','ios']),
        'customer_id': f"C{str(random.randint(1,30000)).zfill(7)}",
        'amount': round(np.random.uniform(1.0, 15.0), 2),   # micro txns
        'is_fraud': 1,
        'risk_score': round(np.random.uniform(72, 98), 1),
    })
df_fraud1 = pd.DataFrame(fraud1_rows)

# ─── FRAUD SCENARIO 2: High-value web fraud in UK / DE (days 18-22) ─────────
print("Injecting fraud scenario 2: high-value web fraud in UK/DE…")
fraud2_n = 1400
fraud2_start = DATE_START + timedelta(days=18)
fraud2_end   = DATE_START + timedelta(days=22)
f2_sec = int((fraud2_end - fraud2_start).total_seconds())
fraud2_rows = []
for _ in range(fraud2_n):
    co = random.choice(['UK','DE'])
    region = random.choice(REGIONS_BY_COUNTRY[co])
    fraud2_rows.append({
        'timestamp': fraud2_start + timedelta(seconds=random.randint(0, f2_sec)),
        'channel': 'web',
        'country': co, 'region': region,
        'segment': np.random.choice(['regular','high_value'], p=[0.5,0.5]),
        'merchant_category': np.random.choice(['luxury','electronics','travel'],
                                               p=[0.45,0.35,0.20]),
        'device_type': 'desktop',
        'customer_id': f"C{str(random.randint(1,30000)).zfill(7)}",
        'amount': round(np.random.lognormal(np.log(1800), 0.5), 2),
        'is_fraud': 1,
        'risk_score': round(np.random.uniform(65, 95), 1),
    })
df_fraud2 = pd.DataFrame(fraud2_rows)

# ─── FRAUD SCENARIO 3: New-customer segment call-center wave (days 24-28) ───
print("Injecting fraud scenario 3: new-customer call-center wave…")
fraud3_n = 1200
fraud3_start = DATE_START + timedelta(days=24)
fraud3_end   = DATE_START + timedelta(days=28)
f3_sec = int((fraud3_end - fraud3_start).total_seconds())
fraud3_rows = []
for _ in range(fraud3_n):
    co = np.random.choice(['NG','BR','IN'], p=[0.4,0.35,0.25])
    region = random.choice(REGIONS_BY_COUNTRY[co])
    fraud3_rows.append({
        'timestamp': fraud3_start + timedelta(seconds=random.randint(0, f3_sec)),
        'channel': 'call_center',
        'country': co, 'region': region,
        'segment': 'new',
        'merchant_category': np.random.choice(['crypto_exchange','travel'], p=[0.6,0.4]),
        'device_type': 'unknown',
        'customer_id': f"C{str(random.randint(1,30000)).zfill(7)}",
        'amount': round(np.random.lognormal(np.log(500), 0.6), 2),
        'is_fraud': 1,
        'risk_score': round(np.random.uniform(70, 99), 1),
    })
df_fraud3 = pd.DataFrame(fraud3_rows)

# ── Combine ──────────────────────────────────────────────────────────────────
df = pd.concat([df_base, df_fraud1, df_fraud2, df_fraud3], ignore_index=True)
df['transaction_id'] = ['TXN' + hashlib.md5(str(i).encode()).hexdigest()[:10].upper()
                        for i in range(len(df))]
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date.astype(str)
df['hour'] = df['timestamp'].dt.hour
df = df.sort_values('timestamp').reset_index(drop=True)

print(f"Total rows: {len(df):,}  |  Fraud rows: {df['is_fraud'].sum():,}  "
      f"|  Fraud rate: {df['is_fraud'].mean()*100:.2f}%")

# ── Analytics tables ─────────────────────────────────────────────────────────
def alert_level(fraud_rate, baseline_fr, volume_ratio):
    if fraud_rate > baseline_fr * 3.5 or volume_ratio > 4:
        return 'Critical'
    elif fraud_rate > baseline_fr * 2.0 or volume_ratio > 2:
        return 'Elevated'
    return 'Normal'

# ── 1. Daily overview ────────────────────────────────────────────────────────
daily = (df.groupby('date').agg(
    volume=('transaction_id','count'),
    total_amount=('amount','sum'),
    fraud_count=('is_fraud','sum'),
    avg_amount=('amount','mean'),
).reset_index())
daily['fraud_rate'] = (daily['fraud_count'] / daily['volume'] * 100).round(3)
daily['total_amount'] = daily['total_amount'].round(2)
daily['avg_amount']   = daily['avg_amount'].round(2)
# Rolling 7-day baseline fraud rate
baseline_fr = daily['fraud_rate'].mean() / 100
daily_list = daily.to_dict(orient='records')

# ── 2. By channel ────────────────────────────────────────────────────────────
ch_agg = (df.groupby(['date','channel']).agg(
    volume=('transaction_id','count'),
    fraud_count=('is_fraud','sum'),
    total_amount=('amount','sum'),
).reset_index())
ch_agg['fraud_rate'] = (ch_agg['fraud_count'] / ch_agg['volume'] * 100).round(3)
ch_agg['total_amount'] = ch_agg['total_amount'].round(2)

# Summary by channel
ch_summary = (df.groupby('channel').agg(
    volume=('transaction_id','count'),
    fraud_count=('is_fraud','sum'),
    total_amount=('amount','sum'),
    avg_amount=('amount','mean'),
).reset_index())
ch_summary['fraud_rate'] = (ch_summary['fraud_count']/ch_summary['volume']*100).round(3)
ch_summary['total_amount'] = ch_summary['total_amount'].round(2)
ch_summary['avg_amount']   = ch_summary['avg_amount'].round(2)
ch_baseline = {r['channel']: r['fraud_rate']/100 for _,r in ch_summary.iterrows()}
# Overall channel baseline
overall_ch_fr = df['is_fraud'].mean()
for _,r in ch_summary.iterrows():
    bfr = ch_baseline.get(r['channel'], overall_ch_fr)
    ch_summary.loc[ch_summary['channel']==r['channel'],'alert_level'] = \
        alert_level(r['fraud_rate']/100, bfr * 0.7, 1)
ch_summary_list  = ch_summary.to_dict(orient='records')
ch_daily_list    = ch_agg.to_dict(orient='records')

# ── 3. By geography ──────────────────────────────────────────────────────────
geo_agg = (df.groupby(['country','region']).agg(
    volume=('transaction_id','count'),
    fraud_count=('is_fraud','sum'),
    total_amount=('amount','sum'),
    avg_amount=('amount','mean'),
).reset_index())
geo_agg['fraud_rate'] = (geo_agg['fraud_count']/geo_agg['volume']*100).round(3)
geo_agg['total_amount'] = geo_agg['total_amount'].round(2)
geo_agg['avg_amount']   = geo_agg['avg_amount'].round(2)
global_fr = df['is_fraud'].mean()
geo_agg['alert_level'] = geo_agg.apply(
    lambda r: alert_level(r['fraud_rate']/100, global_fr, r['volume']/df['volume'].nunique()
                          if hasattr(df,'volume') else 1), axis=1)
geo_list = geo_agg.sort_values('fraud_count', ascending=False).to_dict(orient='records')

# Country summary
country_agg = (df.groupby('country').agg(
    volume=('transaction_id','count'),
    fraud_count=('is_fraud','sum'),
    total_amount=('amount','sum'),
).reset_index())
country_agg['fraud_rate'] = (country_agg['fraud_count']/country_agg['volume']*100).round(3)
country_agg['alert_level'] = country_agg.apply(
    lambda r: alert_level(r['fraud_rate']/100, global_fr, 1), axis=1)
country_list = country_agg.sort_values('fraud_count', ascending=False).to_dict(orient='records')

# ── 4. By segment ────────────────────────────────────────────────────────────
seg_agg = (df.groupby(['date','segment']).agg(
    volume=('transaction_id','count'),
    fraud_count=('is_fraud','sum'),
    total_amount=('amount','sum'),
).reset_index())
seg_agg['fraud_rate'] = (seg_agg['fraud_count']/seg_agg['volume']*100).round(3)
seg_agg['total_amount'] = seg_agg['total_amount'].round(2)

seg_summary = (df.groupby('segment').agg(
    volume=('transaction_id','count'),
    fraud_count=('is_fraud','sum'),
    total_amount=('amount','sum'),
    avg_amount=('amount','mean'),
).reset_index())
seg_summary['fraud_rate'] = (seg_summary['fraud_count']/seg_summary['volume']*100).round(3)
seg_summary['total_amount'] = seg_summary['total_amount'].round(2)
seg_summary['avg_amount']   = seg_summary['avg_amount'].round(2)
seg_baseline = {r['segment']: r['fraud_rate']/100 for _,r in seg_summary.iterrows()}
for _,r in seg_summary.iterrows():
    bfr = seg_baseline.get(r['segment'], global_fr)
    seg_summary.loc[seg_summary['segment']==r['segment'],'alert_level'] = \
        alert_level(r['fraud_rate']/100, bfr * 0.7, 1)
seg_summary_list = seg_summary.to_dict(orient='records')
seg_daily_list   = seg_agg.to_dict(orient='records')

# ── 5. Merchant category summary ─────────────────────────────────────────────
mc_agg = (df.groupby('merchant_category').agg(
    volume=('transaction_id','count'),
    fraud_count=('is_fraud','sum'),
    total_amount=('amount','sum'),
).reset_index())
mc_agg['fraud_rate'] = (mc_agg['fraud_count']/mc_agg['volume']*100).round(3)
mc_agg['alert_level'] = mc_agg.apply(
    lambda r: alert_level(r['fraud_rate']/100, global_fr, 1), axis=1)
mc_list = mc_agg.sort_values('fraud_count', ascending=False).to_dict(orient='records')

# ── 6. Alert list ─────────────────────────────────────────────────────────────
alerts = []

# Channel-level alerts
for _,r in ch_summary.iterrows():
    if r['alert_level'] in ('Elevated','Critical'):
        reason = (f"Fraud rate {r['fraud_rate']:.1f}% vs global avg "
                  f"{global_fr*100:.1f}%. "
                  f"{r['fraud_count']:,} suspected frauds on {r['channel']} channel.")
        next_steps = ("Review recent mobile transactions for card-testing patterns. "
                      "Consider temporary velocity caps on new accounts.")
        alerts.append({
            'id': f"CH-{r['channel'].upper()[:3]}",
            'type':'Channel', 'bucket': r['channel'],
            'alert_level': r['alert_level'],
            'fraud_count': int(r['fraud_count']),
            'fraud_rate': float(r['fraud_rate']),
            'volume': int(r['volume']),
            'reason': reason, 'next_steps': next_steps,
        })

# Geo-level alerts
for _,r in geo_agg[geo_agg['alert_level'].isin(['Elevated','Critical'])].head(10).iterrows():
    reason = (f"{r['country']} / {r['region']}: fraud rate {r['fraud_rate']:.1f}% "
              f"with {r['fraud_count']:,} fraud transactions.")
    next_steps = "Flag region for enhanced authentication. Review linked device fingerprints."
    alerts.append({
        'id': f"GEO-{r['country']}-{r['region'][:3].upper()}",
        'type':'Geography', 'bucket': f"{r['country']} / {r['region']}",
        'alert_level': r['alert_level'],
        'fraud_count': int(r['fraud_count']),
        'fraud_rate': float(r['fraud_rate']),
        'volume': int(r['volume']),
        'reason': reason, 'next_steps': next_steps,
    })

# Segment alerts
for _,r in seg_summary.iterrows():
    if r['alert_level'] in ('Elevated','Critical'):
        reason = (f"Segment '{r['segment']}': fraud rate {r['fraud_rate']:.1f}%. "
                  f"Estimated loss ${r['total_amount']*r['fraud_rate']/100:,.0f}.")
        next_steps = "Enforce step-up verification. Consider segment-level velocity rules."
        alerts.append({
            'id': f"SEG-{r['segment'].upper()[:4]}",
            'type':'Segment', 'bucket': r['segment'],
            'alert_level': r['alert_level'],
            'fraud_count': int(r['fraud_count']),
            'fraud_rate': float(r['fraud_rate']),
            'volume': int(r['volume']),
            'reason': reason, 'next_steps': next_steps,
        })

alerts.sort(key=lambda x: (0 if x['alert_level']=='Critical' else 1, -x['fraud_count']))

# ── 7. Sample case rows (top 200 fraud txns for case view) ───────────────────
case_rows = (df[df['is_fraud']==1]
             .sort_values('risk_score', ascending=False)
             .head(200)
             [['transaction_id','timestamp','customer_id','amount','channel',
               'country','region','merchant_category','segment','risk_score']]
             .copy())
case_rows['timestamp'] = case_rows['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
case_rows['amount'] = case_rows['amount'].round(2)
case_list = case_rows.to_dict(orient='records')

# ── 8. Global KPIs ───────────────────────────────────────────────────────────
total_vol   = len(df)
total_fraud = int(df['is_fraud'].sum())
fraud_rate  = round(df['is_fraud'].mean()*100, 3)
total_amt   = round(df['amount'].sum(), 2)
est_loss    = round(df[df['is_fraud']==1]['amount'].sum(), 2)
n_critical  = sum(1 for a in alerts if a['alert_level']=='Critical')
n_elevated  = sum(1 for a in alerts if a['alert_level']=='Elevated')

kpis = {
    'total_volume': total_vol,
    'total_fraud':  total_fraud,
    'fraud_rate':   fraud_rate,
    'total_amount': total_amt,
    'est_loss':     est_loss,
    'n_critical':   n_critical,
    'n_elevated':   n_elevated,
    'date_range':   f"{DATE_START.strftime('%b %d')} – {DATE_END.strftime('%b %d, %Y')}",
}

# ── Assemble payload ─────────────────────────────────────────────────────────
payload = {
    'kpis':          kpis,
    'daily':         daily_list,
    'ch_summary':    ch_summary_list,
    'ch_daily':      ch_daily_list,
    'geo':           geo_list,
    'country':       country_list,
    'seg_summary':   seg_summary_list,
    'seg_daily':     seg_daily_list,
    'merchant':      mc_list,
    'alerts':        alerts,
    'cases':         case_list,
    'scenarios': [
        {
            'name': 'Scenario 1 – Mobile Card-Testing (Romania)',
            'period': 'Days 10-12 (Jun 8-10)',
            'description': 'A bot network tested stolen card numbers via the mobile app targeting Romanian users. ~2,800 micro-transactions (€1–€15) across electronics and clothing. High transaction velocity from shared IP blocks.',
        },
        {
            'name': 'Scenario 2 – High-Value Web Fraud (UK / DE)',
            'period': 'Days 18-22 (Jun 16-20)',
            'description': '~1,400 high-value fraudulent purchases ($500–$5,000+) on the web channel in UK and Germany. Concentrated in luxury, electronics, and travel merchant categories using compromised premium account credentials.',
        },
        {
            'name': 'Scenario 3 – New-Customer Call-Center Wave (NG / BR / IN)',
            'period': 'Days 24-28 (Jun 22-26)',
            'description': '~1,200 fraudulent transactions via the call-center channel targeting newly-onboarded customers in Nigeria, Brazil, and India. High proportion directed to crypto exchanges and travel — typical money-mule laundering path.',
        },
    ],
}

out_path = '/sessions/inspiring-fervent-cerf/mnt/outputs/fraud_data.json'
with open(out_path, 'w') as f:
    json.dump(payload, f, default=str)

print(f"\n✅ Data saved → {out_path}")
print(f"   KPIs: {kpis}")
print(f"   Alerts: {len(alerts)} total  |  Critical: {n_critical}  |  Elevated: {n_elevated}")
