[![DOI](https://zenodo.org/badge/682751872.svg)](https://zenodo.org/doi/10.5281/zenodo.11168263)

# BioExtremes
Project funded by CIRES IRP 2023

The main objective of this project is to develop an open-source tool that facilitates the use and integration of the new generation of space-borne laser scanners and imaging spectrometers for studies on biodiversity and extreme events. The specific objectives are: 1. Understand the effects of anomalous rainfall and wind gusts on mangrove ecosystem homogenization worldwide, and 2. Assess the role of species diversity in ecosystem response to extreme events.

![image](https://github.com/earthlab/BioExtremes/assets/67020853/773b417a-e15d-454a-b20a-948994084da9)

The *Bioextremes open-source tool* has the following features:

## 1. Subsetting and Downloading GEDI Data

- Granule-level filter tool: can be used to determine the URLs of granules intersecting a polygon, bounding box, or a union or intersection of such shapes - mangrovegranules.py  
- Shot-level filter tool: can be used to discard irrelevant or low-quality data according to the user’s specifications from within a granule after it is downloaded - mangroveshots.py 

## 2. Downloading ERA-5 data and comparison with IBTrACS wind speeds

- Download ERA-5 instantaneous 10m wind speed: can be used to download ERA5 measurements of the 10m instantaneous wind speed and total precipitation from each 1x1 degree tile in an AOI - era5tiles.py
- IBTrACS and ERA5 maximum wind speeds comparison: can be used to calculate cyclone-force winds from the ERA5 instantaneous 10m wind speed - windspeedcomparison.py

## 3. Thres
