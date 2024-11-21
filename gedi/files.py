import os
import pandas as pd


def group_csv_by_year(in_dir: str, out_dir: str, file_level: str):
    years = set()
    for file in os.listdir(in_dir):
        years.add(int(file[9:13]))

    for year in years:
        year_data = []
        for file in os.listdir(in_dir):
            if int(file[9:13]) == year:
                year_data.append(pd.read_csv(os.path.join(in_dir, file)))

        p = pd.concat(year_data, ignore_index=True)
        p.to_csv(os.path.join(out_dir, f'gedi_{file_level}_{year}_combined.csv'))
