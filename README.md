# BioExtremes
Project funded by CIRES IRP 2023

The main objective of this project is to develop an open-source tool that facilitates the use and integration of the 
new generation of space-borne laser scanners and imaging spectrometers for studies on biodiversity and extreme events. 
The specific objectives are: 1. Understand the effects of anomalous rainfall and wind gusts on mangrove ecosystem 
homogenization worldwide, and 2. Assess the role of species diversity in ecosystem response to extreme events.

![image](https://github.com/earthlab/BioExtremes/assets/67020853/773b417a-e15d-454a-b20a-948994084da9)

## Running the Code

### Prerequisites

Ensure you have the following:
-	Python 3.8+
-	Required Python packages (install via requirements.txt):
```bash
pip install -r requirements.txt
```
-	NASA EarthData account for GEDI data download. If you do not have an account you can register at
	https://urs.earthdata.nasa.gov/users/new. 
-	NASA EarthData credentials set as BEX_USER and BEX_PWD environment variables

Or run the code using Docker:
```bash
docker container run -it earthlabcu/bio_extremes
```

### Suggested Workflow

#### 1. Identify Overlapping GEDI Files

The first step in your analysis should be to identify GEDI files that overlap with mangrove areas. This is done using find_gedi_files_that_overlap_mangroves.py.

Example Command:
```bash
python bin/find_gedi_files_that_overlap_mangroves.py --file_level L2A --start_date 2019-01-01 --end_date 2022-12-31
```

This command will:
-	Search for GEDI files at the specified file level (L2A or L2B).
-	Filter the files based on the provided date range (e.g., 2019-01-01 to 2022-12-31).
-	Identify files that overlap with known mangrove forest areas.
-	Write a CSV file with the overlapping gedi files to default location data/gedi/L2A_overlapping_gedi_files.csv

Note: You should run this command for both L2A and L2B file levels separately if you want to include both in your analysis:
```bash
python bin/find_gedi_files_that_overlap_mangroves.py --file_level L2B --start_date 2019-01-01 --end_date 2022-12-31
```

#### 2. Download overlapping GEDI files

Next, use these csv files to download the overlapping GEDI files with bin/download_gedi.py
Example Command:
```bash
python bin/download_gedi.py --file_level L2A --gedi_overlaps_csv data/gedi_L2A_overlapping_gedi_files.csv
```

This command will:  
-	Download each file in the overlaps csv to the default location data/gedi/L2A
-   Combine each file by year to the default location data/gedi/gedi_L2A_(year)_combined.csv

#### 3. Download era5 climate data

Use bin/download_era5.py to download the monthly era5 reanalysis precipitation data.
Example Command:
```bash
python bin/download_era5.py --dataset monthly --start_date 1979-01-01 --end_date 2022-12-31
```
This command will:
-	Search for monthly era5 total precipitation files.
-	Filter the files based on the provided date range (e.g., 1979-01-01 to 2022-12-31).
-	Convert each h5 file to a tif file
-	Write each tif file to the default storage location data/era5/tp 

Use bin/download_era5.py to download the hourly era5 reanalysis wind data.
Example Command:
```bash
python bin/download_era5.py --dataset hourly --start_date 1979-01-01 --end_date 2022-12-31 --hour_filter 0,6,12,18
```

This command will:
-	Search for hourly era5 max 10-m wind gust files.
-	Filter the files based on the provided date range (e.g., 1979-01-01 to 2022-12-31).
-	Convert each h5 file to a tif file and only keep the 0th, 6th, 12th, and 18th hour from each h5 file.
-	Write each tif file to the default storage location data/era5/i10fg


#### 4. Calculate extreme weather thresholds at each mangrove location
For each mangrove location we can both calculate a drought threshold and assign an extreme wind value. These values can 
then be written to a tif file. 

Use bin/write_extreme_thresholds_tif.py to write an extreme weather tif file for both wind and drought
Example Drought Command:
```bash
python bin/write_extreme_thresholds_tif.py drought --era5_dir data/era5/tp
```

This command will:
-	Combine the values of each era5 total precipitation file from 1979-2009 at each mangrove location
-	Calculate the 5th percentile cutoff value at each mangrove location
-	Write a tif file containing the drought threshold at each mangrove location to data/drought_thresholds.tif


Example Extreme Wind Command:
```bash
python bin/write_extreme_thresholds_tif.py wind --era5_dir data/era5/i10fg --threhsold 33
```
This command will:
-	Write a tif file containing the extreme wind threshold of 33 m/s at each mangrove location to data/extreme_wind_thresholds.tif


#### 5. Calculate extreme weather events at each mangrove location
Use the drought and extreme wind thresholds to calculate the intensity, duration, frequency, and time since last extreme event

Example Drought Command:
```bash
python bin/write_extreme_events_tif.py --type drought --threshold_tif data/drought_thresholds.tif --era5_dir data/era5/tp --end_year 2018 --window 3
```
This command will:
-	Identify extreme drought events for each mangrove location as at least a 3 month streak of total precipitation
below the drought threshold from the beginning of the era5 record to 2018-12-31 
-	Calculate the intensity, duration, frequency, and time since (I,D,F,T) the most intense drought event at each mangrove location
-	Write a tif file with the I, D, F, T at each mangrove location to the default location data/drought_2019.tif 

Example Wind Command:
```bash
python bin/write_extreme_events_tif.py --type wind --threshold_tif data/extreme_wind_thresholds.tif --era5_dir data/era5/i10fg --end_year 2018
```
This command will:
-	Identify extreme drought events for each mangrove location as at least a single max 10-m max wind gust above the extreme wind threshold
from the beginning of the era5 record to 2018-12-31
-	Calculate the intensity, duration, frequency, and time since (I,D,F,T) the most intense wind event at each mangrove location
-	Write a tif file with the I, D, F, T at each mangrove location to the default location data/extreme_wind_2019.tif 

#### 6. Match extreme weather events with GEDI data
Use the  combined GEDI csv and extreme weather tif files to match GEDI points to the extreme weather events at each 
mangrove location. When several GEDI points fall within a single mangrove location the median of the values is taken.

Example GEDI / era5 matching command:
```bash
python bin/combine_gedi_and_extreme_events.py --drought_path data/drought_2019.tif --wind_path data/extreme_wind_2019.tif --gedi_csvs data/gedi/gedi_l2a_2019_combined.csv data/gedi/gedi_l2b_2019_combined.csv --output_dir data/gedi_era5_combined/2019 
```
This command will:
-	Match each era5 extreme weather point to the median of any matching L2A and L2B GEDI points and add them as a row in a dataframe
-	Split the dataframe by marine region and species richness range 
-	Write each resulting dataframe to a csv file at data/gedi_era5_combined/2019/

#### 7. a) (Optional) Combine gedi+era5 yearly dataframes
You may want to combine data from several years into one csv before plotting the data
Example dataframe combine command:
```bash
python bin/combine_gedi_extreme_events_dataframes.py --year_dirs data/gedi_era5_combined/2019 data/gedi_era5_combined/2020 --output_dir data/gedi_era5_combined/2019_2020_combined 
```
This command will:
-	Combine each csv file in data/gedi_era5_combined/2019 with its corresponding csv file in data/gedi_era5_combined/2020
-	Write each combined csv file to data/gedi_era5_combined/2019_2020_combined

#### 7. b) Plot the regressions and create tables for the combined gedi and extreme event data
Use the rows in each gedi + extreme event data csv to calculate the linear regression between each gedi (dependent) and
extreme event type (independent) variable. Plots are created with titles and axis labels. Plots will be created that display 
the eco regions and their regressions in one place as well as the species richness. Violin plots of the gedi data will also be created.
Example plotting command:
```bash
python bin/plot_gedi_extreme_events.py --input_dir data/gedi_era5_combined/2019_2020_combined --output_dir data/regressions
```
This command will:
- Calculate the regressions for each marine region, GEDI, and extreme event combination and combine the marine regions on one plot. Saves the plot to `data/regressions`.
- Calculate the regressions for each species richness class, GEDI, and extreme event combination and combine the species richness classes on one plot. Saves the plot to `data/regressions`.
- Calculate the regressions for each GEDI and extreme event combination for all data points globally. Saves the plot to `data/regressions`.
- Create violin plots and tables for each GEDI data set and writes them to `data/regressions`.