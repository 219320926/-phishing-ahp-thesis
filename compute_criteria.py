import json, re, datetime as dt, csv
from brand_matcher import BrandMatcher

matcher = BrandMatcher('brand_reference.csv')
N_REF_BRANDS = 71
CAP_HOURS = 4422  # 95th percentile of observed active spans

INFRASTRUCTURE_DENYLIST = {
    "ipfs.io", "sites.google.com", "urlz.fr", "tinyurl.com", "is.gd",
    "cutt.ly", "bit.ly", "t.co", "goo.gl", "rebrand.ly", "s3.amazonaws.com",
    "storage.googleapis.com", "weebly.com", "wixsite.com", "github.io",
    "netlify.app", "vercel.app", "herokuapp.com", "firebaseapp.com",
    "000webhostapp.com", "blogspot.com", "wordpress.com",
}


def url_features(domain):
    parts = domain.split(".")
    is_ip_host = 1 if all(p.isdigit() for p in parts if p) and len(parts) == 4 else 0
    subdomain_count = max(0, len(parts) - 2)
    return {"is_ip_host": is_ip_host, "subdomain_count": subdomain_count}


def estimate_presence_rate(first_seen, last_seen, observations, polls_per_day=2):
    span_days = max((last_seen - first_seen) / 86400, 1 / polls_per_day)
    expected_polls = span_days * polls_per_day
    return min(observations / expected_polls, 1.0)


rows = []
for m in range(1, 13):
    month = f"2025-{m:02d}"
    with open(f'historical_snapshots/metadata_{month}.json', encoding='utf-8') as f:
        snapshot = json.load(f)

    month_start = dt.datetime.strptime(month, '%Y-%m').replace(tzinfo=dt.timezone.utc).timestamp()
    next_month = (dt.datetime.strptime(month, '%Y-%m').replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    month_end = next_month.replace(tzinfo=dt.timezone.utc).timestamp()

    cohort = {d: v for d, v in snapshot.items()
              if month_start <= v['first_seen'] < month_end and d not in INFRASTRUCTURE_DENYLIST}

    n = len(cohort)
    deceptive = presence_sum = financial = n_matched = 0
    matched_brands = set()
    spans_hours = []

    for domain, meta in cohort.items():
        feats = url_features(domain)
        if feats['is_ip_host'] == 1 or feats['subdomain_count'] > 2:
            deceptive += 1
        presence_sum += estimate_presence_rate(meta['first_seen'], meta['last_seen'], meta['observations'])
        spans_hours.append((meta['last_seen'] - meta['first_seen']) / 3600)
        result = matcher.match(domain)
        if result.brand:
            matched_brands.add(result.brand)
            n_matched += 1
            if result.sector == 'Financial Services':
                financial += 1

    c1 = deceptive / n
    c2 = presence_sum / n
    c3 = len(matched_brands) / N_REF_BRANDS
    mean_hours = sum(spans_hours) / len(spans_hours)
    c4 = max(0.0, 1 - min(mean_hours, CAP_HOURS) / CAP_HOURS)
    c6 = financial / n_matched if n_matched > 0 else 0.0

    rows.append({'month': month, 'n_domains': n, 'C1': c1, 'C2': c2, 'C3': c3, 'C4': c4, 'C6': c6})
    print(f"{month}: n={n:5d}  C1={c1:.4f}  C2={c2:.4f}  C3={c3:.4f}  C4={c4:.4f}  C6={c6:.4f}")

# C5 from changelog.md
with open('../openphish-pihole/changelog.md', encoding='utf-8') as f:
    content = f.read()
entries = content.split('### ')[1:]
monthly_adding = {}
for entry in entries:
    lines = entry.strip().splitlines()
    header = lines[0]
    ts_str = re.sub(r'\+00:00$', '', header.replace(' Changelog', '').strip())
    try:
        ts = dt.datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S.%f')
    except ValueError:
        continue
    month = ts.strftime('%Y-%m')
    for line in lines[1:]:
        line = line.strip().lstrip('- ').strip()
        if line.startswith('Adding'):
            found = re.findall(r'\d+', line)
            if found:
                monthly_adding[month] = monthly_adding.get(month, 0) + int(found[0])

cap_count = max(monthly_adding.get(r['month'], 0) for r in rows)
for r in rows:
    r['C5'] = monthly_adding.get(r['month'], 0) / cap_count

with open('monthly_criteria_series.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['month', 'n_domains', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6'])
    writer.writeheader()
    writer.writerows(rows)

print("\nSaved monthly_criteria_series.csv")
print(f"C5 cap (max monthly additions observed): {cap_count}")