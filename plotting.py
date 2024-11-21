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
        elif plot_type == 'global':
            print(files_to_plot)
            self.plot_combined(files_to_plot, 'global', plot_type)

    def plot_combined(self, csv_files: List[str], base_name: str, plot_type):
        dependent_vars = ['rh98', 'pai', 'fhd']
        for dep_var in dependent_vars:
            for i, indep_var in enumerate(self.rain_indep_vars + self.wind_indep_vars):
                print(f"Processing: {dep_var} vs {indep_var}")
                if plot_type == 'global':
                    self._plot_csv_file_quantiles(csv_files, dep_var, indep_var, base_name, plot_type)
                else:
                    self._plot_csv_files(csv_files, dep_var, indep_var, base_name, plot_type, i==0)
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
            print([os.path.join(path, file) for file in os.listdir(path) if file.startswith('species_richness')])
            return [os.path.join(path, file) for file in os.listdir(path) if file.startswith('species_richness')]
        if plot_type == 'eco_regions':
            return [os.path.join(path, file) for file in os.listdir(path) if not file.startswith('species_richness')]
        if plot_type == 'global':
            return [os.path.join(path, file) for file in os.listdir(path) if not file.endswith('speci')]
        return [os.path.join(path, file) for file in os.listdir(path) if not file.startswith('.')]

    def _plot_csv_file_quantiles(self, csv_files, dep_var, indep_var, base_name, plot_type):
        # Initialize variables
        fig, ax = plt.subplots()
        labels = []
        x_values, y_values = [], []

        # Process each CSV file
        for i, csv_file in enumerate(csv_files):
            x, y, label = self._process_csv_file(csv_file, dep_var, indep_var, plot_type)
            if x is None or y is None:
                continue

            x_values.extend(x)
            y_values.extend(y)
            labels.append(label)

        # Plot for the current CSV
        self._fit_and_plot_quantiles(x_values, y_values, ax)

        # Finalize and save the combined plot
        self._finalize_combined_plot(ax, x_values, y_values, indep_var, dep_var, base_name)

    def _plot_csv_files(self, csv_files, dep_var, indep_var, base_name, plot_type, tables: bool):
        # Initialize variables
        fig, ax = plt.subplots()
        labels = []
        x_values, y_values = [], []
        all_y_values = []

        # Process each CSV file
        for i, csv_file in enumerate(csv_files):
            x, y, label = self._process_csv_file(csv_file, dep_var, indep_var, plot_type)
            if x is None or y is None:
                continue  # Skip if no valid data

            x_values.extend(x)
            y_values.extend(y)
            labels.append(label)
            all_y_values.append(y)

            # Plot for the current CSV
            self._fit_and_plot_combined(x, y, csv_file, i, ax)

        # Finalize and save the combined plot
        self._finalize_combined_plot(ax, x_values, y_values, indep_var, dep_var, base_name)

        if tables:
            # Create and save the violin plot
            self._create_violin_plot(all_y_values, labels, dep_var, plot_type, base_name)

            # Compute and save the summary statistics table
            self._create_summary_statistics_table(all_y_values, labels, dep_var, plot_type, base_name)

    def _process_csv_file(self, csv_file, dep_var, indep_var, plot_type):
        csv = pd.read_csv(csv_file)
        duration_column = 'wind_duration' if indep_var in self.wind_indep_vars else 'drought_duration'
        c = csv[duration_column]

        if not any(c.values > 0):
            return None, None, None  # No valid data

        idx = c >= 0
        x = csv[indep_var].values[idx]
        y = csv[dep_var].values[idx]

        # Filter out NaN values
        valid = ~np.isnan(y)
        if dep_var == 'rh98':
            valid &= y <= 68
        x, y = x[valid], y[valid]

        # Generate label
        if plot_type == 'eco_regions':
            label = ' '.join([w.capitalize() for w in os.path.basename(csv_file).replace('.csv', '').split('_')])
        else:
            label = self._range_transform(csv_file)

        return x, y, label

    def _finalize_combined_plot(self, ax, x_values, y_values, indep_var, dep_var, base_name):
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()

        # Scatter plot of all data points
        ax.scatter(x_values, y_values, color='gray', alpha=0.10, zorder=1)

        # Set axis limits
        if indep_var == 'wind_frequency':
            ax.set_xlim(-0.01, 0.6)
        else:
            ax.set_xlim(x_min, x_max)
        ax.set_ylim(max(0, y_min), y_max)

        # Add labels and legend
        self._add_plot_labels(dep_var, indep_var, ax)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

        # Save the plot
        output_path = os.path.join(self.output_dir, f'{base_name}_{dep_var}_{indep_var}.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def _create_violin_plot(self, all_y_values, labels, dep_var, plot_type, base_name):
        fig_violin, ax_violin = plt.subplots()
        sns.violinplot(data=all_y_values, ax=ax_violin)

        # Set x-ticks and labels
        ax_violin.set_xticks(range(len(labels)))
        ax_violin.set_xticklabels(labels, rotation=45, ha='right')

        # Titles and labels
        if plot_type == 'eco_regions':
            title = f'Violin Plot for {dep_var.upper()} across Marine Regions'
            x_label = 'Marine Region'
        elif plot_type == 'species_richness':
            title = f'Violin Plot for {dep_var.upper()} across Species Richness'
            x_label = 'Species Richness'
        else:
            title = f'Violin Plot for {dep_var.upper()}'
            x_label = ''

        ax_violin.set_title(title)
        ax_violin.set_xlabel(x_label)
        ax_violin.set_ylabel(self.dep_var_map[dep_var])

        # Save the violin plot
        output_path = os.path.join(self.output_dir, f'{base_name}_{dep_var}_violin.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig_violin)

    def _create_summary_statistics_table(self, all_y_values, labels, dep_var, plot_type, base_name):
        summary_stats = []

        # Compute statistics for each dataset
        for label, data in zip(labels, all_y_values):
            data_series = pd.Series(data)
            q1 = data_series.quantile(0.25)
            median = data_series.median()
            q3 = data_series.quantile(0.75)
            summary_stats.append([label, round(q1, 2), round(median, 2), round(q3, 2), len(data)])

        # Create DataFrame for the table
        if dep_var == 'rh98':
            unit = '(m)'
        elif dep_var == 'fhd':
            unit = ''
        else:
            unit = r'$(m^2/m^2)$'

        if plot_type == 'eco_regions':
            x_label = 'Marine Region'
        elif plot_type == 'species_richness':
            x_label = 'Species Richness'
        else:
            x_label = ''

        columns = [x_label, f"25th Percentile {unit}", f"Median {unit}", f"75th Percentile {unit}", "n"]
        summary_df = pd.DataFrame(summary_stats, columns=columns)

        # Plot the table using matplotlib
        fig, ax = plt.subplots(figsize=(9, len(labels) * 0.5))
        ax.axis('tight')
        ax.axis('off')

        table = ax.table(cellText=summary_df.values, colLabels=summary_df.columns, cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.5, 1.5)

        # Save the table as a figure
        title = f"Summary Statistics of {dep_var.upper()} per {x_label}"
        plt.title(title)
        output_path = os.path.join(self.output_dir, f"{base_name}_{dep_var}_summary_statistics_table.png")
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
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

    def _fit_and_plot_quantiles(self, x, y, ax):
        quantiles = [0.5, 0.7, 0.8, 0.9]  # Specify the desired quantiles
        X = sm.add_constant(x)

        for j, q in enumerate(quantiles):
            quantile_results = sm.QuantReg(y, X).fit(q=q, max_iter=20000)
            coef = quantile_results.params
            if len(coef) > 1 and 0 < abs(coef[1]) < 3500:
                pred_values = coef[0] + coef[1] * np.array(x)
                sorted_vals = sorted(zip(x, pred_values), key=lambda v: v[0])

                ax.plot([v[0] for v in sorted_vals], [v[1] for v in sorted_vals],
                        zorder=2,
                        linewidth=2,
                        label=f" | Q={q} | Slope={coef[1]:.3f}"
                        )

        return ax.get_xlim(), ax.get_ylim()

    def _add_plot_labels(self, dep_var, indep_var, ax, title_addendum: str = None):
        indep_var_map = {
            'wind_intensity': 'Extreme Wind Intensity (m/s)',
            'wind_duration': 'Extreme Wind Duration (years)',
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
