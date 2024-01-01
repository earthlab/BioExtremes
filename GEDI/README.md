This folder contains a variety of tools for accessing, subsetting, and downloading GEDI L2A, L2B, and L1B data products. Each module is documented below, as well as an example script. Note that the docstrings for public classes and functions provide further information on their behavior and implementation.

# Modules

## ```api```
This module implements the ```L2AAPI```, ```L2BAPI```, and ```L1BAPI``` classes, all of which inherit from the ```GEDIAPI``` base class, which defines a basic API for scraping GEDI data from the NASA servers. A ```GEDIAPI``` object needs a valid EarthData username and password to access the data, which it takes from the environment variables ```BEX_USER``` and ```BEX_PWD```. These must be set before the API will work. See [this documentation](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#setting-environment-variables) for how to do this in a conda virtual environment.

```GEDIAPI``` objects expose two useful member functions.
* ```urls_in_date_range()``` returns an iterator over the urls of GEDI files associated with granules between two dates (inclusive). This can be used to confine queries to e.g., a particular year or season, or to view all granules with a wide date range.
* ```process_in_memory_file()``` applies a function to the contents of a GEDI archive file without downloading that file to physical memory. This allows users to extract a small subset of the file's useful data without waiting for hundreds of MB of off-location or low-quality measurements to be written to disk. It is the only attribute though which the ```GEDIAPI``` exposes the data.

## ```granuleconstraint```
Before downloading the large ```.h5``` datasets from the NASA server, a user should determine which of them contain data of interest. This can be done using ```GranuleConstraint``` objects from this module. A ```GranuleConstraint``` is a functor which takes as argument the url of a GEDI granule's associated ```.xml``` metadata file, and returns whether the granule intersects a region of interest. This is determined using the bounding polygon included in the metadata, which requires geometry routines implemented in the ```Spherical``` folder. ```GranuleConstraint``` is an abstract class, and it has two subclasses which allow users to specify different types of region of interest:
* ```RegionGC``` corresponds to the interior region of a ```Spherical.SimplePiecewiseArc``` object, e.g. a Polygon.
* ```CompositeGC``` corresponds to a conjuction or disjunction of other constraints. For instance, by disjoining ```RegionGC``` objects, a ```CompositeGC``` can represent a union of Polygons, sometimes referred to as a disjoint Polygon.

## ```shotconstraint```
While granule constraints can determine which ```.h5``` files contain data of interest, they cannot filter out the off-location or low-quality shots from within each file. The ```ShotConstraint``` functor exists for this purpose. ```ShotConstraint``` objects are called on a DataFrame representing the contents of a GEDI ```.h5``` file, and they drop in-place the rows corresponding to shots which fail to pass a constraint. A basic ```ShotConstraint``` only drops rows flagged for low-quality or degraded data, but subclasses enforce further constraints:
* A ```LatLonBox``` is a ```ShotConstraint``` which additionally requires that shots be located within a bounding box.
* A ```Buffer``` is a ```ShotConstraint``` which additionally requires that shots be located within a fixed Haversince distance of a finite set of points on the Earth.

## ```download```
This module contains a single public method, ```downloadandfilterurls```, which applies a ```shotconstraint.ShotConstraint``` to capture the relevant data from a list of granules in a DataFrame or a ```.csv``` file. It allows multithreading to accelerate downloads manyfold on HPC clusters.

# Code Examples
Downloading GEDI data is time-consuming, so a notebook is not a practical format for a tutorial. Instead, see the example scripts in the top directory, ```mangrovegranules.py``` and ```mangroveshots.py```. These two scripts perform successive jobs to find the granules, then the shots, containing high-quality data from the locations of mangrove forest according to the 2020 [Global Mangrove Watch](https://data.unep-wcmc.org/datasets/45) record. Note that the granule-level filtering is performed by a ```granuleconstraint.CompositeGC``` object representing the union of all tiles in the GMW dataset. The shot-level filtering uses a ```shotconstraint.Buffer``` around the individual points in the dataset.
