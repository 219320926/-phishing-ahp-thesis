import subprocess
from datetime import datetime, timedelta
import json

target_commits = {}
for m in range(1, 13):
    month_str = f"2025-{m:02d}"
    if m == 12:
        month_end = datetime(2026, 1, 1) - timedelta(days=1)
    else:
        month_end = datetime(2025, m+1, 1) - timedelta(days=1)
    target_date = month_end + timedelta(days=182)
    target_date_str = target_date.strftime('%Y-%m-%d')

    result = subprocess.run(
        ['git', 'log', f'--before={target_date_str}', '-1', '--format=%H %ai'],
        capture_output=True, text=True,
        cwd='../openphish-pihole'
    )
    line = result.stdout.strip()
    if line:
        commit_hash = line.split()[0]
        commit_date = ' '.join(line.split()[1:3])
        target_commits[month_str] = [commit_hash, commit_date]
        print(f"{month_str}: target={target_date_str}, found commit {commit_hash[:10]} @ {commit_date}")
    else:
        print(f"{month_str}: NO COMMIT FOUND before {target_date_str}")

with open('target_commits.json', 'w') as f:
    json.dump(target_commits, f, indent=2)

print("\nSaved target_commits.json")