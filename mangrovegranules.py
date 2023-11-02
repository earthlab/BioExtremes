"""Save the names of granules containing GMW points."""

import os
from datetime import date
from multiprocessing import freeze_support, Pool

from GMW import gmw
from GEDI.api import L2AAPI
from GEDI.granuleconstraint import RegionGC, CompositeGC


"""
Specify the location of the Global Mangrove Watch data, and the number of parallel process.
"""
# gmwdir = "/pl/active/earthlab/bioextremes/gmw_v3_2020/"; nproc = os.cpu_count()
gmwdir = "/Users/fcseidl/Downloads/gmw_v3_2020/"; nproc = 3


"""
This conditional block with freeze_support() prevents certain warnings.
"""
if __name__ == "__main__":
    freeze_support()

    """
    Use the GMW.gmw module to obtain bounding boxes for each 1x1 degree cell of the global grid containing mangroves.
    """
    print("Loading bounding boxes of GMW tiles...")
    names = gmw.get_tile_names(gmwdir)
    tiles = gmw.get_tiles(names)

    """
    Use the GEDI.api module to connect to earthdata servers and obtain metadata for L2A granules. Other products, e.g. 
    L1B, can be handled similarly, but since we are only interested in granule metadata which is shared between 
    products, we won't do that here.
    """
    print("Checking authentication with https://urs.earthdata.nasa.gov...")
    api = L2AAPI()
    api.check_credentials()

    """
    The GEDI.granuleconstraint module is used to determine which granules are of interest. In this case, we create a 
    composite constraint which accepts granules if and only if they intersect one of the mangrove cells obtained above. 
    The module is capable of constraining granules to arbitrary unions or intersections of polygons or bounding boxes.
    """
    constraint = CompositeGC(
        constraints=[RegionGC(tile, api) for tile in tiles],
        disjunction=True
    )

    """
    This GEDI.api method gives an iterator over every (in this case, L2A) file in the GEDI archive with a certain 
    extension. We choose the .xml extension, as these files contain the bounding polygons of each granule. This date 
    range contains 74121 granules.
    """
    urls = api.urls_in_date_range(
        t_start=date(2019, 1, 1),
        t_end=date(2023, 9, 30),
        suffix='.xml'
    )

    """
    This block performs the brunt of the computation, which is why parallelism is employed here. As the loop runs, it 
    will print every granule with an associated index, a boolean value indicating if the granule passes the constraint 
    specified above, and the link to the granule's associated xml metadata file. Output can be redirected to store this 
    information permanently, so that it can be used to selectively download granules for shot-level subsetting.
    """
    print(f"Parallelizing over {nproc} processes...")
    with Pool(nproc) as pool:
        n = 1
        print("index, accepted, url")
        for accept, url in pool.imap_unordered(constraint, urls):
            print(f"{n}, {accept}, {url}")
            n += 1




