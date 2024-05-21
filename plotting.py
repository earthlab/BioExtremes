from itertools import combinations, permutations
import os

import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.optimize import curve_fit


def model_function(x, a, b, c):
    return a * np.exp(-b * x) + c


def all_unique_permutations(vars):
    # Generate permutations
    all_permutations = []
    # Permutations with one item
    for item in vars:
        all_permutations.append((item,))
    # Permutations with two items
    for perm in permutations(vars, 2):
        all_permutations.append(perm)
    # Permutations with three items
    for perm in permutations(vars, 3):
        all_permutations.append(perm)
    # Permutations with four items (all items)
    all_permutations.append(tuple(vars))
    # Print all permutations

    b = []
    for p in [sorted(v) for v in all_permutations]:
        if p not in b:
            b.append(p)

    return b


#std_err


def plot_multivariate(out_dir, linear: bool = False):
    dependent_vars = ['rh_98', 'pai', 'fhd']
    l2a_csv = pd.read_csv('l2a_2019.csv')
    l2b_csv = pd.read_csv('l2b_2019.csv')

    for dep_var in dependent_vars:
        csv = l2a_csv if dep_var in l2a_csv.columns else l2b_csv

        wind_indep_vars = [
            'wind_intensity',
            'wind_duration',
            'wind_frequency',
            'wind_time_since_last_event'
        ]
        rain_indep_vars = [
            'rain_frequency',
            'rain_intensity',
            'rain_duration',
            'rain_time_since_last_event'
        ]

        r2s = []
        for indep_vars in all_unique_permutations(rain_indep_vars + wind_indep_vars):
            x_cols = []
            # idx = np.where(csv['wind_duration' if any(
            #     indep_var in wind_indep_vars for indep_var in indep_vars) else 'rain_duration'] >= 0)
            idx = np.where(np.logical_and(csv['wind_duration'] >= 0,  csv['rain_duration'] >= 0))
            for indep_var in indep_vars:
                x_cols.append(csv[indep_var].values[idx])
            x = np.stack(x_cols).T
            y = csv[dep_var].values[idx]

            X = sm.add_constant(x)
            #X = x

            quantiles = [
                0.5, 0.70, 0.80,
                0.90]

            # fit_functor, plot_functor = (lambda x: x, lambda x: x) if 'time_since_last_event' in indep_var else (np.log, np.exp)
            fit_functor, plot_functor = (lambda x: x, lambda x: x) if linear else (np.log, np.exp)

            # Fit quantile regression models for each quantile level
            quantile_results = []
            for quantile in quantiles:
                model = sm.QuantReg(fit_functor(y), X)
                result = model.fit(q=quantile)
                quantile_results.append(result)

            # Print summary results for each quantile
            #plt.scatter(x, y, label='Data', alpha=0.50)

            # Plot original data
            # fig = plt.figure()
            # ax = fig.add_subplot(111, projection='3d')  # For 3D plotting
            # print(X[:, 0], X[:, 1])
            # ax.scatter(X[:, 0], X[:, 1], y, label='Original Data')

            # Plot lines of best fit for each quantile
            for i, result in enumerate(quantile_results):
                try:
                    # Generate predictions
                    print(dep_var)
                    print(result.summary())
                    summary = result.summary().as_text()
                    r2s.append(result.prsquared)
                    with open(os.path.join(out_dir, f'{dep_var}_vs_wind_{quantiles[i]}_multivariate.txt'), 'w+') as f:
                        f.write(summary)
                    #predictions = result.predict(X)

                    # Plot predictions
                    # If you have more than 2 independent variables, you may need to adjust how you plot the predictions
                    # For 3D plotting
                    # ax.plot_trisurf(X[:, 0], X[:, 1], predictions, linewidth=0.2, antialiased=True, cmap='viridis',
                    #                 alpha=0.5, label=f'Quantile {quantiles[i]}')
                    #
                    # # Add labels and legend
                    # ax.set_xlabel('Wind Duration')
                    # ax.set_ylabel('Wind Intensity')
                    # ax.set_zlabel('PAI')
                    # plt.legend()
                    # plt.title('Quantile Regression with Multiple Independent Variables')
                    # plt.show()

                    # Extract coefficients for the current quantile
                    # coef = result.params
                    #
                    # # Compute predicted values for the current quantile
                    # pred_values = coef[0] + coef[1] * np.array(xs)
                    # print(coef[0], coef[1])
                    #
                    # # Calculate R-squared value for the current quantile
                    # r_squared = result.prsquared
                    #
                    # x_y = sorted(np.stack([xs, pred_values], axis=1), key=lambda x: x[0])
                    #
                    # # Plot line of best fit for the current quantile with label including R-squared
                    # plt.plot([v[0] for v in x_y], plot_functor(np.array([v[1] for v in x_y])),
                    #          label=f'Quantile {quantiles[i]} (R^2 = {r_squared:.2f})')
                    # summary = result.summary().as_text()
                    #
                    # with open(os.path.join(sub_dir, f'{dep_var}_{indep_var}_{quantiles[i]}_percentile_summary.txt'),
                    #           'w+') as f:
                    #     f.write(summary)

                except:
                    continue

                # # Add labels and legend
                # x_labels = {
                #     'wind_duration': 'Max Extreme Wind Event Duration (Hours)',
                #     'wind_frequency': 'Frequency of Extreme Wind Events',
                #     'wind_intensity': 'Max Extreme Wind Event Intensity (m/s)',
                #     'wind_time_since_last_event': 'Time Since Last Wind Event (Hours)',
                #     'wind_s': 'Max Extreme Wind Event Composite Score',
                #     'rain_time_since_last_event': 'Time Since Last Rain Event (Months)',
                #     'rain_duration': 'Max Extreme Rain Event Duration (Months)',
                #     'rain_frequency': 'Frequency of Extreme Rain Events',
                #     'rain_intensity': 'Max Extreme Rain Event Intensity (m)',
                #     'rain_s': 'Max Extreme Rain Event Composite Score'
                # }
                # y_labels = {
                #     'fhd': 'Foliage Height Diversity',
                #     'pai': 'Plant Area Index (m^2/m^2)',
                #     'rh_98': 'Relative Height 98 (m)'
                # }
                #
                # title_x = {
                #     'wind_duration': 'Extreme Wind',
                #     'wind_frequency': 'Extreme Wind',
                #     'wind_intensity': 'Extreme Wind',
                #     'wind_time_since_last_event': 'Extreme Wind',
                #     'rain_time_since_last_event': 'Extreme Rain',
                #     'rain_duration': 'Extreme Rain',
                #     'rain_frequency': 'Extreme Rain',
                #     'rain_intensity': 'Extreme Rain',
                #     'rain_s': 'Extreme Rain'
                # }
                #
                # title_y = {
                #     'fhd': 'Foliage Height Diversity',
                #     'pai': 'Plant Area Index',
                #     'rh_98': 'Relative Height 98'
                # }
                #
                # plt.xlabel(x_labels[indep_var])
                # plt.ylabel(y_labels[dep_var])
                # plt.legend()
                # plt.title(f'{title_y[dep_var]} (2019) vs {title_x[indep_var]} (1979-2018) \n Quantile Regression')
                # plt.savefig(f'{sub_dir}/{dep_var}_{indep_var}.png')
                # plt.cla()
                # plt.clf()

        return r2s






def plot_all_combinations(out_dir, linear: bool = False):
    dependent_vars = ['rh_98', 'pai', 'fhd']
    l2a_csv = pd.read_csv('l2a_2019.csv')
    l2b_csv = pd.read_csv('l2b_2019.csv')

    for dep_var in dependent_vars:
        csv = l2a_csv if dep_var in l2a_csv.columns else l2b_csv

        wind_indep_vars = [
            #'wind_intensity', 'wind_duration', 'wind_frequency', 'wind_time_since_last_event'
        ]
        rain_indep_vars = [
            'rain_frequency', 'rain_intensity', 'rain_duration', 'rain_time_since_last_event'
        ]

        for indep_var in rain_indep_vars + wind_indep_vars:

            sub_dir = os.path.join(out_dir, f'{dep_var}_vs_{indep_var}')
            os.makedirs(sub_dir, exist_ok=True)

            idx = np.where(csv['wind_duration' if indep_var in wind_indep_vars else 'rain_duration'] >= 0)
            x = csv[indep_var].values[idx]
            y = csv[dep_var].values[idx]

            # xs = []
            # ys = []
            # bins = np.linspace(np.min(csv[indep_var].values[idx]), np.max(csv[indep_var].values[idx]), 100)
            # for i in range(1, len(bins)):
            #     bidx = np.where(np.logical_and(bins[i - 1] <= csv[indep_var].values[idx], csv[indep_var].values[idx] < bins[i]))
            #     xs.append(np.mean(csv[indep_var].values[idx][bidx]))
            #     ys.append(np.std(csv[dep_var].values[idx][bidx]))
            #
            # xs = [v for v in xs if not np.isnan(v)]
            # ys = [v for v in ys if not np.isnan(v)]

            xs = x
            ys = y

            if indep_var in [
                'wind_duration', 'wind_time_since_last_event'
            ]:
                xs *= 4

            X = sm.add_constant(xs)

            quantiles = [0.5, 0.70, 0.80, 0.90]

            #fit_functor, plot_functor = (lambda x: x, lambda x: x) if 'time_since_last_event' in indep_var else (np.log, np.exp)
            fit_functor, plot_functor = (lambda x: x, lambda x: x) if linear else (np.log, np.exp)

            # Fit quantile regression models for each quantile level
            quantile_results = []
            for quantile in quantiles:
                model = sm.QuantReg(fit_functor(ys), X)
                result = model.fit(q=quantile)
                quantile_results.append(result)

            # Print summary results for each quantile
            plt.scatter(xs, ys, label='Data', alpha=0.50)

            # Plot lines of best fit for each quantile
            for i, result in enumerate(quantile_results):
                try:
                    # Extract coefficients for the current quantile
                    coef = result.params

                    # Compute predicted values for the current quantile
                    pred_values = coef[0] + coef[1] * np.array(xs)
                    print(coef[0], coef[1])

                    # Calculate R-squared value for the current quantile
                    r_squared = result.prsquared

                    x_y = sorted(np.stack([xs, pred_values], axis=1), key=lambda x: x[0])

                    # Plot line of best fit for the current quantile with label including R-squared
                    plt.plot([v[0] for v in x_y], plot_functor(np.array([v[1] for v in x_y])), label=f'Quantile {quantiles[i]} (R^2 = {r_squared:.2f})')
                    summary = result.summary().as_text()

                    with open(os.path.join(sub_dir, f'{dep_var}_{indep_var}_{quantiles[i]}_percentile_summary.txt'), 'w+') as f:
                        f.write(summary)

                except:
                    continue

            # Add labels and legend
            x_labels = {
                'wind_duration': 'Max Extreme Wind Event Duration (Hours)',
                'wind_frequency': 'Frequency of Extreme Wind Events',
                'wind_intensity': 'Max Extreme Wind Event Intensity (m/s)',
                'wind_time_since_last_event': 'Time Since Last Wind Event (Hours)',
                'wind_s': 'Max Extreme Wind Event Composite Score',
                'rain_time_since_last_event': 'Time Since Last Drought (Months)',
                'rain_duration': 'Max Drought Duration (Months)',
                'rain_frequency': 'Frequency of Drought Events',
                'rain_intensity': 'Max Drought Event Intensity (m)',
                'rain_s': 'Max Drought Event Composite Score'
            }
            y_labels = {
                'fhd': 'Foliage Height Diversity',
                'pai': 'Plant Area Index (m^2/m^2)',
                'rh_98': 'Relative Height 98 (m)'
            }

            title_x = {
                'wind_duration': 'Extreme Wind',
                'wind_frequency': 'Extreme Wind',
                'wind_intensity': 'Extreme Wind',
                'wind_time_since_last_event': 'Extreme Wind',
                'rain_time_since_last_event': 'Extreme Rain',
                'rain_duration': 'Drought',
                'rain_frequency': 'Drought',
                'rain_intensity': 'Drought',
                'rain_s': 'Drought'
            }

            title_y = {
                'fhd': 'Foliage Height Diversity',
                'pai': 'Plant Area Index',
                'rh_98': 'Relative Height 98'
            }

            plt.xlabel(x_labels[indep_var])
            plt.ylabel(y_labels[dep_var])
            plt.legend()
            plt.title(f'{title_y[dep_var]} (2019) vs {title_x[indep_var]} (1979-2018) \n Quantile Regression')
            plt.savefig(f'{sub_dir}/{dep_var}_{indep_var}.png', dpi=300)
            plt.cla()
            plt.clf()

            # slope, intercept, r, p, se = stats.linregress(x, y[idx])
            # print(dep_var, indep_var, r, p)

        # all_combinations = []
        # for r in range(1, len(wind_indep_vars + rain_indep_vars) + 1):
        #     all_combinations.extend(combinations(wind_indep_vars + rain_indep_vars, r))

        # for comb in all_unique_permutations(wind_indep_vars + rain_indep_vars):
        #     print(comb)
        #
        #     wind_idx = None
        #     if 'wind_duration' in comb:
        #         wind_idx = 'wind_duration'
        #     elif 'wind_intensity' in comb:
        #         wind_idx = 'wind_intensity'
        #     elif 'wind_frequency' in comb:
        #         wind_idx = 'wind_frequency'
        #     elif 'wind_time_since_last_event':
        #         wind_idx = 'wind_time_since_last_event'
        #
        #     wind_col = None
        #     if wind_idx is not None:
        #         wind_col = csv[wind_idx].values[percentile]
        #
        #     rain_idx = None
        #     if 'rain_duration' in comb:
        #         rain_idx = 'rain_duration'
        #     elif 'rain_intensity' in comb:
        #         rain_idx = 'rain_intensity'
        #     elif 'rain_frequency' in comb:
        #         rain_idx = 'rain_frequency'
        #     elif 'rain_time_since_last_event':
        #         rain_idx = 'rain_time_since_last_event'
        #
        #     rain_col = None
        #     if rain_idx is not None:
        #         rain_col = csv[rain_idx].values[percentile]
        #
        #     idx = np.logical_and(wind_col >= duration_cutoff_wind if wind_col is not None else
        #                          np.ones_like(percentile[0]),
        #                          rain_col >= duration_cutoff_rain if rain_col is not None else np.ones_like(percentile[0])
        #                          )
        #
        #     x_cols = []
        #     for indep_var in comb:
        #         if indep_var not in ['wind_frequency']:
        #             x_cols.append(np.array([np.log(v) for v in csv[indep_var].values[percentile][idx]]))
        #         else:
        #             x_cols.append(csv[indep_var].values[percentile][idx])
        #
        #     x = np.stack(x_cols).T
        #     y_train = csv[dep_var].values[percentile][idx]
        #
        #     model = LinearRegression()
        #     model.fit(x, y_train)
        #
        #     y_pred = model.predict(x)
        #
        #     residuals = y_train - y_pred

            # Fit the model to the data
            # try:
            #     print('popt')
            #     popt = curve_fit(model_function, x, y_train)
            #     print(*popt)
            # except:
            #     continue
            # # Calculate predicted values
            # y_pred = model_function(x, *popt)
            # #
            # # # Calculate R-squared value
            # ss_total = np.sum((y_train - np.mean(y_train)) ** 2)
            # ss_res = np.sum((y_train - y_pred) ** 2)
            # r_squared = 1 - (ss_res / ss_total)
            #
            # print(comb, "R-squared:", r_squared)

            # # Plot residuals
            # plt.figure(figsize=(8, 6))
            # plt.scatter(y_pred, residuals)
            # plt.xlabel('Predicted Values')
            # plt.ylabel('Residuals')
            # plt.title('Residual Plot')
            # plt.axhline(y=0, color='r', linestyle='--')
            # plt.grid(True)
            # plt.savefig(f'residual_plot_{dep_var}.png')
            #
            # # Plot predicted vs. actual values
            # plt.figure(figsize=(8, 6))
            # plt.scatter(y_train, y_pred)
            # plt.plot([y_train.min(), y_train.max()], [y_train.min(), y_train.max()], 'k--', lw=2)
            # plt.xlabel('Actual Values')
            # plt.ylabel('Predicted Values')
            # plt.title('Actual vs. Predicted Plot')
            # plt.grid(True)
            # plt.savefig(f'predicted_vs_actual_plot_{dep_var}.png')

            # Print regression coefficients
            #print(f"Regression Coefficients {dep_var}:", model.coef_)

            # Calculate R-squared
            # r2 = r2_score(y_train, y_pred)
            # print(r2)
            # if r2 > max_r2:
            #     # if max_r2 != 0:
            #     #     print(comb, r2)
            #     max_r2 = r2
            #
            # # Calculate Mean Squared Error
            # mse = mean_squared_error(y_train, y_pred)

            # if len(comb) == 8:
            #     model = sm.OLS(y_train, sm.add_constant(x)).fit()
            #
            #     # Get the p-values of the coefficients
            #     p_values = model.pvalues
            #
            #     print(comb, p_values)

            #print(f"Mean Squared Error {dep_var}:", mse)
    #print(max_r2)
