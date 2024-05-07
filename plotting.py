from itertools import combinations

import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd
import statsmodels.api as sm


def plot_all_combinations(percentile_cutoff, duration_cutoff_wind, duration_cutoff_rain):
    dependent_vars = ['rh98', 'pai', 'fhd']
    l2a_csv = pd.read_csv('l2a_2019.csv')
    l2b_csv = pd.read_csv('l2b_2019.csv')

    for dep_var in dependent_vars:
        max_r2 = 0
        csv = l2a_csv if dep_var in l2a_csv.columns else l2b_csv

        percentile = np.where(csv[dep_var].values >= np.percentile(csv[dep_var].values, percentile_cutoff))

        indep_vars = [
            'wind_intensity', 'wind_duration', 'wind_frequency',
            #'wind_time_since_last_event',
            'rain_intensity', 'rain_duration', 'rain_frequency',
            #'rain_time_since_last_event'
        ]

        all_combinations = []
        for r in range(1, len(indep_vars) + 1):
            all_combinations.extend(combinations(indep_vars, r))

        for comb in all_combinations:

            wind_idx = None
            if 'wind_duration' in comb:
                wind_idx = 'wind_duration'
            elif 'wind_intensity' in comb:
                wind_idx = 'wind_intensity'
            elif 'wind_frequency' in comb:
                wind_idx = 'wind_frequency'
            elif 'wind_time_since_last_event':
                wind_idx = 'wind_time_since_last_event'

            wind_col = None
            if wind_idx is not None:
                wind_col = csv[wind_idx].values[percentile]

            rain_idx = None
            if 'rain_duration' in comb:
                rain_idx = 'rain_duration'
            elif 'rain_intensity' in comb:
                rain_idx = 'rain_intensity'
            elif 'rain_frequency' in comb:
                rain_idx = 'rain_frequency'
            elif 'rain_time_since_last_event':
                rain_idx = 'rain_time_since_last_event'

            rain_col = None
            if rain_idx is not None:
                rain_col = csv[rain_idx].values[percentile]

            idx = np.logical_and(wind_col >= duration_cutoff_wind if wind_col is not None else
                                 np.ones_like(percentile[0]), rain_col >= duration_cutoff_rain if rain_col is not None else np.ones_like(percentile[0]))

            x_cols = []
            for indep_var in comb:
                x_cols.append(csv[indep_var].values[percentile][idx])

            x = np.stack(x_cols).T
            y_train = csv[dep_var].values[percentile][idx]

            model = LinearRegression()
            model.fit(x, y_train)

            y_pred = model.predict(x)

            residuals = y_train - y_pred

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
            r2 = r2_score(y_train, y_pred)
            if r2 > max_r2:
                if max_r2 != 0:
                    print(comb, r2)
                max_r2 = r2

            # Calculate Mean Squared Error
            mse = mean_squared_error(y_train, y_pred)

            # if len(comb) == 8:
            #     model = sm.OLS(y_train, sm.add_constant(x)).fit()
            #
            #     # Get the p-values of the coefficients
            #     p_values = model.pvalues
            #
            #     print(comb, p_values)

            #print(f"Mean Squared Error {dep_var}:", mse)
    print(max_r2)
