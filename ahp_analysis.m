%% ahp_analysis.m
clear; clc;

criteria_names = {'C1','C2','C3','C4','C5','C6'};
n_criteria = 6;

RI_n6 = 1.24;
CR_threshold = 0.10;
B = 1000;
alpha = 0.05;
rng(42);

%% Step 1: Load data
point_estimates = readtable('criteria_point_estimates.csv');
daily_series = readtable('criteria_daily_series.csv');

f_point = table2array(point_estimates(1, criteria_names));
daily_matrix = table2array(daily_series(:, criteria_names));

fprintf('Loaded %d monthly observations.\n', size(daily_matrix,1));

%% Step 2: Pairwise comparison matrix
pairwise_matrix = f_point' * (1 ./ f_point);
disp('Pairwise comparison matrix:');
disp(array2table(pairwise_matrix, 'VariableNames', criteria_names, 'RowNames', criteria_names));

%% Step 3: Eigenvector decomposition + Consistency Ratio
[weights_point, lambda_max_point, CI_point, CR_point] = compute_ahp_weights(pairwise_matrix, RI_n6);

fprintf('\nPoint-estimate priority weights:\n');
for i = 1:n_criteria
    fprintf('  %s: %.4f\n', criteria_names{i}, weights_point(i));
end
fprintf('lambda_max = %.4f, CI = %.4f, CR = %.4f\n', lambda_max_point, CI_point, CR_point);

%% Step 4: Bootstrap resampling (B=1000)
n_obs = size(daily_matrix, 1);
retained_weights = [];

for b = 1:B
    idx = randi(n_obs, n_obs, 1);
    resample = daily_matrix(idx, :);
    f_resample = mean(resample, 1);
    if any(f_resample <= 0) || any(isnan(f_resample))
        continue;
    end
    matrix_b = f_resample' * (1 ./ f_resample);
    [w_b, ~, ~, cr_b] = compute_ahp_weights(matrix_b, RI_n6);
    if cr_b <= CR_threshold
        retained_weights = [retained_weights; w_b']; %#ok<AGROW>
    end
end

n_retained = size(retained_weights, 1);
fprintf('\nRetained %d / %d bootstrap iterations\n', n_retained, B);

%% Step 5: Summarise bootstrap distributions
boot_mean = mean(retained_weights, 1);
boot_sd = std(retained_weights, 0, 1);
ci_lower = quantile(retained_weights, 0.025, 1);
ci_upper = quantile(retained_weights, 0.975, 1);

[~, rank_order] = sort(boot_mean, 'descend');
ranks = zeros(1, n_criteria);
ranks(rank_order) = 1:n_criteria;

fprintf('\nBootstrap-derived priority weights (real 95%% CIs):\n');
summary_table = table(criteria_names', boot_mean', boot_sd', ci_lower', ci_upper', ranks', ...
    'VariableNames', {'Criterion','Mean','SD','CI_Lower','CI_Upper','Rank'});
summary_table = sortrows(summary_table, 'Rank');
disp(summary_table);
writetable(summary_table, 'table_III_matlab.csv');

%% Step 6: One-sample Hotelling's T^2 test (MANOVA equivalent)
variances = var(retained_weights, 0, 1);
low_variance_idx = find(variances < 1e-8);
usable_idx = setdiff(1:n_criteria, low_variance_idx);
test_idx = usable_idx(1:end-1);
p = length(test_idx);

W_reduced = retained_weights(:, test_idx);
equal_weight_vec = ones(1, p) / n_criteria;
n = size(retained_weights, 1);

W_mean = mean(W_reduced, 1);
S = cov(W_reduced);
fprintf('\nHotelling''s T^2 test running on: %s\n', strjoin(criteria_names(test_idx), ', '));
diff = W_mean - equal_weight_vec;
T2 = n * (diff / S) * diff';
F_stat = ((n - p) / (p * (n - 1))) * T2;
p_value = 1 - fcdf(F_stat, p, n - p);

fprintf('T^2 = %.4f, F(%d,%d) = %.4f, p = %.6g\n', T2, p, n-p, F_stat, p_value);
if p_value < alpha
    fprintf('Reject H0: criterion weights differ significantly from equal weighting.\n');
end

%% Step 7: One-way ANOVA + Tukey HSD
W = retained_weights;
long_weights = reshape(W, [], 1);
long_groups = repmat(criteria_names, n, 1);
long_groups = reshape(long_groups, [], 1);

[p_anova, ~, stats_anova] = anova1(long_weights, long_groups, 'off');
fprintf('\nOne-way ANOVA: p = %.6g\n', p_anova);

figure('Visible', 'off');
[tukey_results, ~, ~, tukey_gnames] = multcompare(stats_anova, 'CType', 'tukey-kramer', 'Display', 'off');
tukey_table = array2table(tukey_results, 'VariableNames', ...
    {'Group1','Group2','LowerCI','MeanDiff','UpperCI','PValue'});
tukey_table.Group1Name = tukey_gnames(tukey_table.Group1);
tukey_table.Group2Name = tukey_gnames(tukey_table.Group2);
disp('Tukey HSD post-hoc comparisons:');
disp(tukey_table(:, {'Group1Name','Group2Name','MeanDiff','LowerCI','UpperCI','PValue'}));
writetable(tukey_table, 'tukey_hsd_matlab.csv');

%% Step 8: Bonferroni-corrected pairwise t-tests
pairs = nchoosek(1:n_criteria, 2);
n_comparisons = size(pairs, 1);
alpha_corrected = alpha / n_comparisons;

fprintf('\nBonferroni-corrected pairwise t-tests (alpha'' = %.6f):\n', alpha_corrected);
for k = 1:n_comparisons
    i = pairs(k,1); j = pairs(k,2);
    [~, p_val, ~, stats_t] = ttest2(W(:,i), W(:,j));
    fprintf('  %s vs %s: t=%.4f, p=%.6g, significant=%d\n', ...
        criteria_names{i}, criteria_names{j}, stats_t.tstat, p_val, p_val<alpha_corrected);
end

fprintf('\nDone.\n');

%% Helper function
function [weights, lambda_max, CI, CR] = compute_ahp_weights(matrix, RI)
    [eigvecs, eigvals] = eig(matrix);
    eigvals = diag(eigvals);
    [lambda_max, max_idx] = max(real(eigvals));
    weights = real(eigvecs(:, max_idx));
    weights = weights / sum(weights);
    n = size(matrix, 1);
    CI = (lambda_max - n) / (n - 1);
    CR = CI / RI;
end




