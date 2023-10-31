"""Save the names of granules containing GMW points."""

from datetime import date
from multiprocessing import freeze_support, Pool

from GMW import gmw
from GEDI.api import L2AAPI
from GEDI.granuleconstraint import RegionGC, CompositeGC


gmwdir = "/Users/fcseidl/Downloads/gmw_v3_2020/"
nproc = 3

if __name__ == "__main__":
    freeze_support()

    print("Loading bounding boxes of GMW tiles...")
    names = gmw.get_tile_names(gmwdir)
    tiles = gmw.get_tiles(names)

    print("Checking authentication with https://urs.earthdata.nasa.gov...")
    api = L2AAPI()
    api.check_credentials()

    # reject granules bounded outside 1 equatorial degree from GMW points
    constraint = CompositeGC(
        constraints=[RegionGC(tile, api) for tile in tiles],
        disjunction=True
    )

    urls = api.urls_in_date_range(
        t_start=date(2019, 1, 1),
        t_end=date(2023, 9, 30),
        suffix='.xml'
    )

    print(f"Parallelizing over {nproc} processes...")
    with Pool(nproc) as pool:
        n = 1
        print("index, accepted, url")
        for accept, url in pool.imap_unordered(constraint, urls):
            print(f"{n}, {accept}, {url}")
            n += 1




