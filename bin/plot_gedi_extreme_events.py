from plotting import Plotter
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Plot data based on different types using the Plotter class."
    )
    parser.add_argument(
        "-i", "--input_dir",
        required=True,
        help="Base directory containing the input data."
    )
    parser.add_argument(
        "-o", "--output_dir",
        required=True,
        help="Directory to save the output plots."
    )
    parser.add_argument(
        "-t", "--plot_type",
        required=False,
        choices=["eco_regions", "species_richness", "global"],
        help="Type of plot to generate. Options: 'eco_regions', 'species_richness', 'global'."
    )

    args = parser.parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir
    plot_type = args.plot_type

    plotter = Plotter(base_data_dir=input_dir, output_dir=output_dir)
    if plot_type is None:
        for plot_type in ["eco_regions", "species_richness", "global"]:
            plotter.plot_all(plot_type)
    else:
        plotter.plot_all(plot_type)