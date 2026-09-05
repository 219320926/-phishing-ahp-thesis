import subprocess, json, os

with open('target_commits.json') as f:
    target_commits = json.load(f)

os.makedirs('historical_snapshots', exist_ok=True)

for month_str, (commit_hash, commit_date) in target_commits.items():
    out_path = f'historical_snapshots/metadata_{month_str}.json'
    result = subprocess.run(
        ['git', 'show', f'{commit_hash}:metadata.json'],
        capture_output=True, text=True,
        cwd='../openphish-pihole'
    )
    if result.returncode == 0 and result.stdout:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        size_kb = os.path.getsize(out_path) / 1024
        print(f"{month_str}: extracted ({size_kb:.0f} KB)")
    else:
        print(f"{month_str}: FAILED - {result.stderr[:200]}")