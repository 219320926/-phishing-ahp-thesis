import pandas as pd
import numpy as np

CRITERIA = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6']
RI_N6 = 1.24
CR_THRESHOLD = 0.10
B = 1000

df = pd.read_csv('monthly_criteria_series.csv')
daily_series = df[CRITERIA]

point_estimates = {c: daily_series[c].mean() for c in CRITERIA}
print("Point estimates (mean across 12 real months):")
for c, v in point_estimates.items():
    print(f"  {c}: {v:.4f}")


def build_pairwise_matrix(f):
    values = np.array([f[c] for c in CRITERIA], dtype=float)
    return values.reshape(-1, 1) / values.reshape(1, -1)


def eigenvector_weights(matrix):
    eigvals, eigvecs = np.linalg.eig(matrix)
    max_idx = np.argmax(eigvals.real)
    lambda_max = eigvals.real[max_idx]
    weights = eigvecs[:, max_idx].real
    weights = weights / weights.sum()
    n = matrix.shape[0]
    ci = (lambda_max - n) / (n - 1)
    cr = ci / RI_N6
    return weights, lambda_max, ci, cr


matrix = build_pairwise_matrix(point_estimates)
print("\nPairwise comparison matrix:")
print(pd.DataFrame(matrix, index=CRITERIA, columns=CRITERIA).round(3))

weights, lambda_max, ci, cr = eigenvector_weights(matrix)
print(f"\nPoint-estimate priority weights: {dict(zip(CRITERIA, np.round(weights, 4)))}")
print(f"lambda_max={lambda_max:.4f}, CI={ci:.4f}, CR={cr:.4f} ({'ACCEPTABLE' if cr <= CR_THRESHOLD else 'EXCEEDS THRESHOLD'})")

rng = np.random.default_rng(42)
n_obs = len(daily_series)
retained_weights = []

for _ in range(B):
    idx = rng.integers(0, n_obs, size=n_obs)
    resample = daily_series.iloc[idx]
    f_resample = {c: resample[c].mean() for c in CRITERIA}
    if any(v <= 0 for v in f_resample.values()):
        continue
    m = build_pairwise_matrix(f_resample)
    w, _, _, r_cr = eigenvector_weights(m)
    if r_cr <= CR_THRESHOLD:
        retained_weights.append(w)

weights_df = pd.DataFrame(retained_weights, columns=CRITERIA)
print(f"\nRetained {len(weights_df)}/{B} bootstrap iterations (CR <= {CR_THRESHOLD})")

summary = pd.DataFrame({
    'mean': weights_df.mean(),
    'sd': weights_df.std(),
    'ci_lower': weights_df.quantile(0.025),
    'ci_upper': weights_df.quantile(0.975),
})
summary['rank'] = summary['mean'].rank(ascending=False).astype(int)
summary = summary.sort_values('rank')

print("\nBootstrap-derived priority weights with real 95% CIs:")
print(summary)

summary.to_csv('table_III_final.csv')
weights_df.to_csv('bootstrap_weight_samples.csv', index=False)
print("\nSaved table_III_final.csv and bootstrap_weight_samples.csv")