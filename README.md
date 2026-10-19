# AHP-Based Phishing Mitigation Prioritisation Framework

Companion code and data for the Master's thesis *Integrating the Analytical Hierarchy Process and Human Indicators in Decision-Making on Phishing Attacks* (Tebogo Mashabane, Cape Peninsula University of Technology).

## What this is

The full pipeline behind the results in Chapters 4 and 5: a twelve-month (January-December 2025), survivorship-bias-corrected phishing-feed dataset, six threat-intelligence proxy criteria (C1-C6) derived from it, and an AHP weighting with bootstrap resampling and descriptive statistical tests. The criteria are proxies computed from feed fields (URL structure, persistence, brand matches, time-in-archive, record counts, financial-sector matches); they are not direct measurements of user behaviour, organisational response or financial loss (thesis Section 3.5.1).

## Inputs included (exact archived data)

- `historical_snapshots/metadata_2025-MM.json.gz`: the archive's `metadata.json` exactly as it existed at each commit listed in `target_commits.json`, taken from `github.com/invisiblethreat/openphish-pihole` (commit SHAs pinned in `target_commits.json`; each month is observed about 182 days after month-end).
- `upstream_changelog/changelog.md`: copy of the archive's `changelog.md` (used only for C5, monthly record counts).
- `brand_reference.csv`: 71-brand reference list (thesis Appendix C).

## Reproduce (Python 3.10+; `pip install pandas numpy scipy statsmodels rapidfuzz`)

```
gunzip -k historical_snapshots/*.gz          # creates metadata_2025-MM.json
mkdir ../openphish-pihole
cp upstream_changelog/changelog.md ../openphish-pihole/changelog.md
python compute_criteria.py                   # -> monthly_criteria_series.csv (Table 4.1 inputs)
python prepare_for_matlab.py                 # -> criteria_point_estimates.csv, criteria_daily_series.csv
python run_ahp.py                            # -> table_III_final.csv, bootstrap_weight_samples.csv (Tables 4.2-4.5)
```
Then run `ahp_analysis.m` in MATLAB (Statistics and Machine Learning Toolbox) from this folder for the cross-validation in Table 4.6 (`table_III_matlab.csv`, `tukey_hsd_matlab.csv`).

`find_target_commits.py` and `extract_snapshots.py` show how the snapshots were originally obtained from a full clone of the archive; they are only needed to repeat that step.

## Table-to-file map

| Thesis item | Produced by | Output file |
|---|---|---|
| Table 4.1 criterion values | compute_criteria.py, prepare_for_matlab.py | monthly_criteria_series.csv, criteria_point_estimates.csv |
| Tables 4.2-4.3 matrix and point weights | run_ahp.py / ahp_analysis.m | printed output; MATLAB output in thesis Appendix B |
| Table 4.4 bootstrap weights (B = 1000, seed 42) | run_ahp.py | table_III_final.csv, bootstrap_weight_samples.csv |
| Hotelling T2, Tukey HSD, Bonferroni tests, sensitivity, rank correlation | ahp_analysis.m | tukey_hsd_matlab.csv, console output (Appendix B) |
| Table 4.5 strategy scores | calculated in the thesis (Table 4.4 weights x literature-informed local scores); no script | illustrative, not reproduced from feed data |
| Table 4.6 Python-MATLAB check | run_ahp.py vs ahp_analysis.m | table_III_final.csv vs table_III_matlab.csv |

Verified: re-running `compute_criteria.py` on these snapshots reproduces `criteria_point_estimates.csv` to full precision.

## Citation

Please cite the associated thesis (see its bibliography).
