import os
import sys
from multiprocessing import Pool
import requests
from typing import List, Tuple
from http.cookiejar import CookieJar
import certifi
import getpass
import re
from datetime import datetime, timedelta
import urllib
from tqdm import tqdm

from bs4 import BeautifulSoup
import numpy as np
from osgeo import gdal

# TODO: Need methods for converting hd5 files to tif that are clipped to mangrove areas. Also isolate only the bands
#  we care about and scale the data

# Extract important layers, convert off-nominals to NaN, scale if necessary, clip, and convert to tif file with only
# necessary bands


class GEDI:
    """
    Defines all the attributes and methods common to the child APIs.
    """
    _BASE_URL = None
    _BASE_FILE_RE = r'_(?P<year>\d{4})(?P<doy>\d{3})(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})_O(?P<orbit>\d+)_(?P<sub_oribt>\d+)_T(?P<track_number>\d+)_(?P<ppds>\d{2})_(?P<pge>\d{3})_(?P<granule>\d{2})_V002\.h5$'

    def __init__(self, lazy: bool = False):
        """
        Initializes the common attributes required for each data type's API
        """
        self._username = os.environ.get('BEX_USER', None)
        self._password = os.environ.get('BEX_PWD', None)
        self._core_count = os.cpu_count()
        self._file_re = None
        self._tif_re = None
        self._dates = None

    @staticmethod
    def retrieve_links(url: str) -> List[str]:
        """
        Creates a list of all the links found on a webpage
        Args:
            url (str): The URL of the webpage for which you would like a list of links

        Returns:
            (list): All the links on the input URL's webpage
        """
        request = requests.get(url)
        soup = BeautifulSoup(request.text, 'html.parser')
        return [link.get('href') for link in soup.find_all('a')]

    @staticmethod
    def _cred_query() -> Tuple[str, str]:
        """
        Ask the user for their urs.earthdata.nasa.gov username and login
        Returns:
            username (str): urs.earthdata.nasa.gov username
            password (str): urs.earthdata.nasa.gov password
        """
        print('Please input your earthdata.nasa.gov username and password. If you do not have one, you can register'
              ' here: https://urs.earthdata.nasa.gov/users/new . For subsequent api initializations you can set the '
              'BEX_USER and BEX_PWD environment variables with your login credentials')
        username = input('Username:')
        password = getpass.getpass('Password:', stream=None)

        return username, password

    def _configure(self) -> None:
        """
        Queries the user for credentials and configures SSL certificates
        """
        if self._username is None or self._password is None:
            username, password = self._cred_query()

            self._username = username
            self._password = password

        # This is a macOS thing... need to find path to SSL certificates and set the following environment variables
        ssl_cert_path = certifi.where()
        if 'SSL_CERT_FILE' not in os.environ or os.environ['SSL_CERT_FILE'] != ssl_cert_path:
            os.environ['SSL_CERT_FILE'] = ssl_cert_path

        if 'REQUESTS_CA_BUNDLE' not in os.environ or os.environ['REQUESTS_CA_BUNDLE'] != ssl_cert_path:
            os.environ['REQUESTS_CA_BUNDLE'] = ssl_cert_path

    def _download(self, query: Tuple[str, str]) -> None:
        """
        Downloads data from the NASA earthdata servers. Authentication is established using the username and password
        found in the local ~/.netrc file.
        Args:
            query (tuple): Contains the remote location and the local path destination, respectively
        """
        link = query[0]
        dest = query[1]

        if os.path.exists(dest):
            return

        pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        pm.add_password(None, "https://urs.earthdata.nasa.gov", self._username, self._password)
        cookie_jar = CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPBasicAuthHandler(pm),
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )
        urllib.request.install_opener(opener)
        myrequest = urllib.request.Request(link)
        response = urllib.request.urlopen(myrequest)
        response.begin()
        with open(dest, 'wb') as fd:
            while True:
                chunk = response.read()
                if chunk:
                    fd.write(chunk)
                else:
                    break

    def _retrieve_dates(self, url: str) -> List[datetime]:
        """
        Finds which dates are available from the server and returns them as a list of datetime objects
        Returns:
            (list): List of available dates on the OPeNDAP server in ascending order
        """
        date_re = r'\d{4}.\d{2}.\d{2}'
        dates = self.retrieve_links(url)
        links = []
        for date in dates:
            if re.match(date_re, date):
                links.append(date)

        return sorted(list(set([datetime.strptime(link, '%Y.%m.%d/') for link in links if re.match(date_re, link) is not
                                None])))

    def download_time_series(self, t_start: datetime = None, t_stop: datetime = None, outdir: str = None) -> str:
        """

        """
        if outdir is None:
            outdir = None  # TODO: Write to project dir somewhere
        else:
            os.makedirs(outdir, exist_ok=True)

        t_start = self._dates[0] if t_start is None else t_start
        t_stop = self._dates[-1] if t_stop is None else t_stop
        date_range = [date for date in self._dates if t_start <= date <= t_stop]
        if not date_range:
            raise ValueError('There is no data available in the time range requested')

        queries = []
        for date in date_range:
            url = urllib.parse.urljoin(self._BASE_URL, date.strftime('%Y') + '.' + date.strftime('%m') + '.' +
                                       date.strftime('%d') + '/')
            files = self.retrieve_links(url)
            for file in files:
                match = re.match(self._file_re, file)
                if match is not None:
                    date_objs = match.groupdict()
                    file_date = datetime(int(date_objs['year']), 1, 1) + timedelta(
                        days=int(date_objs['doy']) - 1, hours=int(date_objs['hour']),  minutes=int(date_objs['minute']),
                        seconds=int(date_objs['second']))

                    if t_start <= file_date <= t_stop:
                        remote = urllib.parse.urljoin(url, file)
                        dest = os.path.join(outdir, file)
                        if os.path.exists(dest):
                            continue
                        req = (remote, dest)
                        if req not in queries:
                            queries.append(req)

        if len(queries) > 0:
            print("Retrieving data... skipping over any cached files")
            try:
                with Pool(int(self._core_count / 4)) as pool:
                    for _ in tqdm(pool.imap_unordered(self._download, queries), total=len(queries)):
                        pass

            except Exception as pe:
                try:
                    _ = [self._download(q) for q in tqdm(queries, position=0, file=sys.stdout)]
                except Exception as e:
                    template = "Download failed: error type {0}:\n{1!r}"
                    message = template.format(type(e).__name__, e.args)
                    print(message)

        print(f'Wrote {len(queries)} files to {outdir}')

        return outdir

    @staticmethod
    def _create_raster(output_path: str, columns: int, rows: int, n_band: int = 1,
                       gdal_data_type: int = gdal.GDT_Float32,
                       driver: str = r'GTiff'):
        """
        Credit:
        https://gis.stackexchange.com/questions/290776/how-to-create-a-tiff-file-using-gdal-from-a-numpy-array-and-
        specifying-nodata-va

        Creates a blank raster for data to be written to
        Args:
            output_path (str): Path where the output tif file will be written to
            columns (int): Number of columns in raster
            rows (int): Number of rows in raster
            n_band (int): Number of bands in raster
            gdal_data_type (int): Data type for data written to raster
            driver (str): Driver for conversion
        """
        # create driver
        driver = gdal.GetDriverByName(driver)

        output_raster = driver.Create(output_path, columns, rows, n_band, eType=gdal_data_type)
        return output_raster

    @staticmethod
    def _numpy_array_to_raster(output_path: str, numpy_array: np.array, geo_transform,
                               projection: str = 'wgs84', n_bands: int = 1, no_data: int = np.nan,
                               gdal_data_type: int = gdal.GDT_Float32):
        """
        Returns a gdal raster data source
        Args:
            output_path (str): Full path to the raster to be written to disk
            numpy_array (np.array): Numpy array containing data to write to raster
            geo_transform (gdal GeoTransform): tuple of six values that represent the top left corner coordinates, the
            pixel size in x and y directions, and the rotation of the image. Example [-126.75, 0.25, 0, 23.875, 0, 0.25]
            n_bands (int): The band to write to in the output raster
            no_data (int): Value in numpy array that should be treated as no data
            gdal_data_type (int): Gdal data type of raster (see gdal documentation for list of values)
        """
        rows, columns = numpy_array.shape[0], numpy_array.shape[1]

        # create output raster
        output_raster = GEDI._create_raster(output_path, int(columns), int(rows), n_bands, gdal_data_type)

        output_raster.SetProjection(projection)
        output_raster.SetGeoTransform(geo_transform)
        for i in range(n_bands):
            output_band = output_raster.GetRasterBand(i+1)
            output_band.SetNoDataValue(no_data)
            output_band.WriteArray(numpy_array[:, :, i] if numpy_array.ndim == 3 else numpy_array)
            output_band.FlushCache()
            output_band.ComputeStatistics(False)

        if not os.path.exists(output_path):
            raise Exception('Failed to create raster: %s' % output_path)

        return output_path


class L2A(GEDI):
    _BASE_URL = 'https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/'

    def __init__(self, lazy: bool = False):
        super().__init__(lazy=lazy)
        self._file_re = r"GEDI02_A" + self._BASE_FILE_RE
        self._dates = self._retrieve_dates(self._BASE_URL)


class L2B(GEDI):
    _BASE_URL = 'https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_B.002/'

    def __init__(self, lazy: bool = False):
        super().__init__(lazy=lazy)
        self._file_re = r"GEDI02_B" + self._BASE_FILE_RE
        self._dates = self._retrieve_dates(self._BASE_URL)


class L1B(GEDI):
    _BASE_URL = 'https://e4ftl01.cr.usgs.gov/GEDI/GEDI01_B.002/'

    def __init__(self, lazy: bool = False):
        super().__init__(lazy=lazy)
        self._file_re = r"GEDI01_B" + self._BASE_FILE_RE
        self._dates = self._retrieve_dates(self._BASE_URL)
