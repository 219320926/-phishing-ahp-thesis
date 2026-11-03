# AHP-Based Phishing Mitigation Prioritisation Framework

Companion code and data for the Master's thesis *Integrating the Analytical Hierarchy Process and Human Indicators in Decision-Making on Phishing Attacks* (Tebogo Mashabane, Cape Peninsula University of Technology).

## What this is

The pipeline behind the results in Chapters 4 and 5: a twelve-month (January to December 2025) dataset reconstructed from historical snapshots of an archive of the OpenPhish free feed, six archive-derived proxy criteria (C1 to C6), the AHP computation, and descriptive resampling and sensitivity analyses. The proxies are computed from archive fields (domain structure, observation counts and spans, brand matches, changelog volume). They are not measurements of user behaviour, organisational response or financial loss. The reconstruction reduces a snapshot-age problem but retains residual survivorship selection (thesis Sections 3.5.1 and 3.5.2). No hypothesis tests are used.

## Inputs included

- `historical_snapshots/metadata_2025-MM.json.gz`: the archive's `metadata.json` as it existed at the commit listed for that month in `target_commits.json`, from `github.com/invisiblethreat/openphish-pihole` (one commit per month, about 181 days after month-end; read with `git show <sha>:metadata.json`).
- `upstream_changelog/changelog.md`: copy of the archive's `changelog.md` (used only for C5).
- `brand_reference.csv`: the 71-brand reference list (thesis Appendix C).
- `monthly_criteria_series.csv`: monthly values of C1 to C6 (thesis Table 4.1).

## Environment

Python 3.14.6, Windows 11. Exact package versions are in `requirements.txt` (`pip install -r requirements.txt`). MATLAB R2026a Update 3 with the Statistics and Machine Learning Toolbox is used for the cross-check only.

## Reproduce

On Windows (Command Prompt, in this folder):

```
pip install -r requirements.txt
python -c "import gzip,shutil,glob; [shutil.copyfileobj(gzip.open(f),open(f[:-3],'wb')) for f in glob.glob('historical_snapshots/*.gz')]"
mkdir ..\openphish-pihole
copy upstream_changelog\changelog.md ..\openphish-pihole\changelog.md
python compute_criteria.py                   # -> monthly_criteria_series.csv
python prepare_for_matlab.py                 # -> criteria_point_estimates.csv, criteria_daily_series.csv
python run_ahp.py                            # -> point weights and bootstrap (Tables 4.2 to 4.4)
python build_cohort_cache.py                 # -> cohort_raw.pkl (needed for the matcher variants)
python resampling_and_sensitivity.py         # -> g1_*, g2_*, g3_*, g4_* CSVs
python summary_tables.py                     # -> r_* CSVs (Tables 4.5 to 4.8 inputs, strategy scenario)
```

On Mac or Linux, replace the unpacking and copy lines with:

```
gunzip -k historical_snapshots/*.gz
mkdir ../openphish-pihole
cp upstream_changelog/changelog.md ../openphish-pihole/changelog.md
```

and run the Python commands as above. The original sequence is kept below for reference.

```
gunzip -k historical_snapshots/*.gz          # creates metadata_2025-MM.json
mkdir ../openphish-pihole
cp upstream_changelog/changelog.md ../openphish-pihole/changelog.md
python compute_criteria.py                   # -> monthly_criteria_series.csv
python prepare_for_matlab.py                 # -> criteria_point_estimates.csv
python run_ahp.py                            # -> point weights and bootstrap (Tables 4.2 to 4.4)
python build_cohort_cache.py                 # -> cohort_raw.pkl (needed for the matcher variants)
python resampling_and_sensitivity.py         # -> g1_*, g2_*, g3_*, g4_* CSVs (resampling, perturbation, variants)
python summary_tables.py                     # -> r_* CSVs (Tables 4.5 to 4.8 inputs, strategy scenario)
```

Then, in MATLAB, change to this folder (`cd 'path\to\this\folder'`) and type `ahp_analysis` in the Command Window. Do not use the editor's Run button on a copy of the script saved elsewhere. This produces the Python-MATLAB comparison for the Python-MATLAB comparison (Table 4.9).
`find_target_commits.py` and `extract_snapshots.py` show how the snapshots were obtained from a full clone of the archive and are needed only to repeat that step.

`ahp_analysis.m` also contains Steps 6 to 8 (Hotelling, ANOVA/Tukey and Bonferroni tests). They are retained only to reproduce the console log in thesis Appendix B and are not used as evidence (thesis Section 3.4.5).

`results_reference/` holds the output files from the runs reported in the thesis, for comparison with your own run. The re-run was checked on Python 3.14.6 and MATLAB R2026a (Windows 11). Results agree with the reference files, apart from differences in the last digits of values that involve eigenvalue calculations (for example `r_sensitivity.csv`). The Python and MATLAB bootstrap means agree to about three decimals, because the two programs use different random-number generators (thesis Section 4.10).

## Table-to-file map

| Thesis item | Produced by | Output file |
|---|---|---|
| Table 4.1 monthly values and spread | compute_criteria.py, summary_tables.py | monthly_criteria_series.csv, r_descriptives.csv |
| Tables 4.2 and 4.3 matrix and point weights | run_ahp.py, ahp_analysis.m | printed output |
| Table 4.4 bootstrap intervals (B = 1,000, seed 42) | run_ahp.py | table_III_final.csv, bootstrap_weight_samples.csv |
| Table 4.5 resampling summaries | resampling_and_sensitivity.py | g1_jackknife.csv, g1_block_bootstrap.csv, g1_rank_probability.csv |
| Table 4.6 reciprocity-preserving rank stability | resampling_and_sensitivity.py | g2_single_perturbation.csv, g2_flip_thresholds.csv, g2_joint_noise.csv, r_sensitivity.csv |
| Table 4.7 normalisation, orientation and matcher variants | resampling_and_sensitivity.py, summary_tables.py | g3_preprocessing.csv, r_orientation.csv |
| Table 4.8 illustrative strategy scores | summary_tables.py | r_strategy_assumptions.csv, r_strategy_dirichlet.csv, r_strategy_localperturb.csv |
| Table 4.9 Python-MATLAB comparison | run_ahp.py vs ahp_analysis.m | table_III_final.csv vs table_III_matlab.csv |

Table 4.8 uses assumed local scores and is an illustration, not a result derived from the feed data.

## Citation

Mashabane, T. 2026. *Integrating the Analytical Hierarchy Process and Human Indicators in Decision-Making on Phishing Attacks*. Master's dissertation, Cape Peninsula University of Technology, Cape Town. Code and data: github.com/219320926/-phishing-ahp-thesis (release v1.0).
