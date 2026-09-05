import pandas as pd

df = pd.read_csv('monthly_criteria_series.csv')
CRITERIA = ['C1', 'C2', 'C3', 'C4', 'C5', 'C6']

# Daily/monthly series - what the bootstrap resamples from
df[CRITERIA].to_csv('criteria_daily_series.csv', index=False)

# Point estimates - single row of means, used for the base pairwise matrix
point_estimates = df[CRITERIA].mean().to_frame().T
point_estimates.to_csv('criteria_point_estimates.csv', index=False)

print("Saved criteria_daily_series.csv and criteria_point_estimates.csv")
print("\nPoint estimates:")
print(point_estimates)