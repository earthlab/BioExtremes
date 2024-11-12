import os
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
import numpy as np
from typing import List
import seaborn as sns


class Plotter:
    def __init__(self, base_data_dir: str, output_dir: str):
        self.base_data_dir = base_data_dir
        self.output_dir = output_dir
        self.wind_indep_vars = ['wind_intensity', 'wind_duration', 'wind_frequency', 'wind_time_since_last_event']
        self.rain_indep_vars = ['drought_frequency', 'drought_intensity', 'drought_duration',
                                'drought_time_since_last_event']
        self.dep_var_map = {
            'rh98': 'Relative Height 98th Percentile (m)',
            'pai': 'Plant Area Index (m^2/m^2)',
            'fhd': 'Foliage Height Diversity'
        }

    def plot_all(self, plot_type: str):
        """Plot all eco regions, species diversity, or separate based on the type."""
        files_to_plot = self._get_files_to_plot(plot_type)
        if plot_type == 'eco_regions':
            print(files_to_plot)
            self.plot_combined(files_to_plot, 'eco_regions_combined', plot_type)
        elif plot_type == 'species_richness':
            files_to_plot = sorted(files_to_plot, key=lambda x: int(os.path.basename(x).split('_')[2]))
            self.plot_combined(files_to_plot, 'species_richness_combined', plot_type)

    def plot_combined(self, csv_files: List[str], base_name: str, plot_type):
        dependent_vars = ['rh98', 'pai', 'fhd']
        for dep_var in dependent_vars:
            for indep_var in self.rain_indep_vars + self.wind_indep_vars:
                print(f"Processing: {dep_var} vs {indep_var}")
                self._plot_csv_files(csv_files, dep_var, indep_var, base_name, plot_type)
                plt.cla()

    @staticmethod
    def _range_transform(s):
        label_name = [w.capitalize() for w in os.path.basename(s).replace('.csv', '').split('_')]
        if label_name[-1].isdigit() and label_name[-2].isdigit():
            label_name[-1] = label_name[-2] + '-' + label_name.pop()
        label_name = ' '.join(label_name)
        return label_name

    def _get_files_to_plot(self, plot_type):
        """Get a list of files to plot based on the plot type."""
        path = self.base_data_dir
        if plot_type == "species_richness":
            return [os.path.join(path, file) for file in os.listdir(path) if file.startswith('species_richness')]
        if plot_type == 'eco_regions':
            return [os.path.join(path, file) for file in os.listdir(path) if not file.startswith('species_richness')]
        return [os.path.join(path, file) for file in os.listdir(path) if not file.startswith('.')]

    def _plot_csv_files(self, csv_files, dep_var, indep_var, base_name, plot_type):
        fig, ax = plt.subplots()
        labels = []
        x_values, y_values = [], []
        all_y_values = []
        for i, csv_file in enumerate(csv_files):
            csv = pd.read_csv(csv_file)

            # Determine the index based on the independent variable condition
            c = csv['wind_duration' if indep_var in self.wind_indep_vars else 'drought_duration']
            if not any([v > 0 for v in c.values]):
                continue
            idx = c >= 0
            x, y = csv[indep_var].values[idx], csv[dep_var].values[idx]

            l = len(y)
            m = [not np.isnan(v) for v in y]
            if dep_var == 'rh98':
                m = np.logical_and(m, [v <= 68 for v in y])
            x, y = x[m], y[m]

            x_values.extend(x)
            y_values.extend(y)

            if plot_type == 'eco_regions':
                labels.append(' '.join([w.capitalize() for w in os.path.basename(csv_file).replace('.csv', '').split('_')]))
            else:
                labels.append(self._range_transform(csv_file))
            all_y_values.append(y)  # Collect y-values for violin plot

            # Plot for the current CSV
            self._fit_and_plot_combined(x, y, csv_file, i, ax)

        # Calculate mean and standard deviation for y-values

        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        ax.scatter(x_values, y_values, color='gray', alpha=0.10, zorder=1)

        if indep_var == 'wind_frequency':
            ax.set_xlim(-0.01, 0.6)
        else:
            ax.set_xlim(x_min, x_max)
        ax.set_ylim(max(0, y_min), y_max)
        # Add labels, legend, and save the plot
        self._add_plot_labels(dep_var, indep_var, ax)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))  # Adjust ncol as needed for columns
        fig.savefig(os.path.join(self.output_dir, f'{base_name}_{dep_var}_{indep_var}.png'), dpi=300,
                    bbox_inches='tight')
        plt.close(fig)

        fig_violin, ax_violin = plt.subplots()
        sns.violinplot(data=all_y_values, ax=ax_violin)

        # Set x-ticks and labels
        ax_violin.set_xticks(range(len(labels)))
        ax_violin.set_xticklabels(labels, rotation=45, ha='right')

        # Titles and labels
        if plot_type == 'eco_regions':
            ax_violin.set_title(f'Violin Plot for {dep_var.upper()} across Marine Region')
            x_label = 'Marine Region'
        elif plot_type == 'species_richness':
            ax_violin.set_title(f'Violin Plot for {dep_var.upper()} across Species Richness')
            x_label = 'Species Richness'
        ax_violin.set_xlabel(x_label)
        ax_violin.set_ylabel(self.dep_var_map[dep_var])

        # Save the violin plot
        fig_violin.savefig(os.path.join(self.output_dir, f'{base_name}_{dep_var}_violin.png'), dpi=300,
                           bbox_inches='tight')
        plt.close(fig_violin)

        # Assuming `all_y_values` is a list of lists or DataFrame and `labels` is a list of strings
        summary_stats = []

        # Compute statistics for each dataset in `all_y_values`
        for i, data in enumerate(all_y_values):
            q1 = pd.Series(data).quantile(0.25)
            median = pd.Series(data).median()
            q3 = pd.Series(data).quantile(0.75)
            summary_stats.append([labels[i], round(q1, 2), round(median, 2), round(q3, 2), len(data)])

        # Create DataFrame for the table
        unit = None
        if dep_var == 'rh98':
            figsize = 9
            unit = '(m)'
        elif dep_var == 'fhd':
            figsize = 9
            unit = ''
        else:
            figsize = 9
            unit = '(m^2/m^2)'

        summary_df = pd.DataFrame(summary_stats, columns=[x_label, f"25th Percentile {unit}", f"Median {unit}",
                                                          f"75th Percentile {unit}", "n"])

        # Plot the table using matplotlib
        fig, ax = plt.subplots(
            figsize=(figsize, len(labels) * 0.5)
        )  # Adjust figure size for better readability
        ax.axis('tight')
        ax.axis('off')

        # Create the table
        table = ax.table(
            cellText=summary_df.values,
            colLabels=summary_df.columns,
            cellLoc='center',
            loc='center'
        )

        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.5, 1.5)

        # Save the table as a figure
        plt.title(f"Summary Statistics Table of {dep_var.upper()} per {x_label}")
        plt.savefig(os.path.join(self.output_dir, f"{base_name}_{dep_var}_summary_statistics_table.png"),
                    bbox_inches='tight', dpi=300)
        plt.close(fig)

    def _fit_and_plot_combined(self, x, y, csv_file, i, ax):
        colors = plt.colormaps['Set1'].colors
        colors = list(colors)
        colors[8] = 'black'
        X = sm.add_constant(x)
        quantile_results = sm.QuantReg(y, X).fit(q=0.5, max_iter=20000)
        coef = quantile_results.params
        if len(coef) > 1 and 0 < abs(coef[1]) < 3500:
            pred_values = coef[0] + coef[1] * np.array(x)
            sorted_vals = sorted(zip(x, pred_values), key=lambda v: v[0])

            ax.plot([v[0] for v in sorted_vals], [v[1] for v in sorted_vals],
                    zorder=2,
                    linewidth=2,
                    color=colors[i % len(colors)],
                    label=self._range_transform(csv_file) + " | " + (f"Slope = {coef[1]:.3f}")
                    )
            return ax.get_xlim, ax.get_ylim

    def _add_plot_labels(self, dep_var, indep_var, ax, title_addendum: str = None):
        indep_var_map = {
            'wind_intensity': 'Extreme Wind Intensity (m/s)',
            'wind_duration': 'Extreme Wind Duration (h)',
            'wind_time_since_last_event': 'Time Since Last Extreme Wind Event (years)',
            'wind_frequency': 'Extreme Wind Frequency (events / year)',
            'drought_intensity': 'Drought Intensity (m)',
            'drought_frequency': 'Drought Frequency (events / year)',
            'drought_duration': 'Drought Duration (months)',
            'drought_time_since_last_event': 'Time Since Last Drought Event (years)'
        }
        title = f"{dep_var.replace('_', ' ').upper()} vs {' '.join([w.capitalize() for w in indep_var.split('_')])} 1979-Present"
        if title_addendum:
            title += '\n' + title_addendum
        ax.set_title(title)
        ax.set_xlabel(indep_var_map[indep_var])
        ax.set_ylabel(self.dep_var_map[dep_var])
        ax.legend()
