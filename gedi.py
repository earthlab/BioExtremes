import os
import sys
from io import BytesIO
from multiprocessing import Pool
from urllib.error import HTTPError

import numpy as np
import requests
from typing import List, Tuple, Iterator
from http.cookiejar import CookieJar
import certifi
import getpass
import re
from datetime import datetime, timedelta, date
import urllib
from tqdm import tqdm
from typing import Callable

from bs4 import BeautifulSoup

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
        self._username = os.environ['BEX_USER']     # TODO: raise a proper exception if these aren't defined
        self._password = os.environ['BEX_PWD']
        self._core_count = os.cpu_count()
        self._file_re = None
        self._tif_re = None
        self._dates = None

    def request_raw_data(self, link: str):
        """
        Request data from the NASA earthdata servers. Authentication is established using the username and password
        found in the local ~/.netrc file.

        :param link: remote location of data file
        :return: raw data returned by the server
        """
        pm = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        pm.add_password(None, "https://urs.earthdata.nasa.gov", self._username, self._password)
        cookie_jar = CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPBasicAuthHandler(pm),
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )
        urllib.request.install_opener(opener)
        myrequest = urllib.request.Request(link)
        try:
            return urllib.request.urlopen(myrequest)
        except HTTPError as e:
            print('An HTTPError occurred, suggesting that your authentication may have failed. \
                    Are your credentials correct?')
            raise e

    def process_in_memory_file(self, link: str, func: Callable, *args, **kwargs):
        """
        Perform an action on the contents of a url while storing them in a memory file in RAM.

        :param link: webpage url
        :param func: Method which takes a file-like object as its first argument and performs the action.
        :param args: Passed to func.
        :param kwargs: Passed to func.
        :return: Result of func([linked file], *args, **kwargs), or None if a memory error occurs.
        """
        response = self.request_raw_data(link)
        response.begin()
        with BytesIO() as memfile:
            try:
                while True:
                    chunk = response.read()
                    if chunk:
                        memfile.write(chunk)
                    else:
                        break
                return func(memfile, *args, **kwargs)
            except MemoryError:
                # TODO: what causes these?
                print(f"Memory error caused failed download from {link}")
                return

    @staticmethod
    def retrieve_links(url: str, suffix: str = "") -> List[str]:
        """
        Creates a list of all the links found on a webpage
        Args:
            url (str): The URL of the webpage for which you would like a list of links
            suffix (str): Only retrieve links with this suffix, e.g. suffix='.png' means only links to png images
                            will be returned.

        Returns:
            (list): All the links on the input URL's webpage ending in the suffix.
        """
        request = requests.get(url)
        soup = BeautifulSoup(request.text, 'html.parser')
        links = [link.get('href') for link in soup.find_all('a')]
        return [link for link in links if link.endswith(suffix)]

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
            print("No download occurred, preexisting file at %s" % dest)
            return

        response = self.request_raw_data(link)
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
        TODO: documentation
        """
        if outdir is None:
            outdir = None  # TODO: Write to project dir somewhere
        else:
            os.makedirs(outdir, exist_ok=True)

        t_start = self._dates[0] if t_start is None else t_start
        t_stop = self._dates[-1] if t_stop is None else t_stop
        date_range = [day for day in self._dates if t_start <= day <= t_stop]
        if not date_range:
            raise ValueError('There is no data available in the time range requested')

        queries = []
        for day in date_range:
            url = urllib.parse.urljoin(self._BASE_URL, day.strftime('%Y') + '.' + day.strftime('%m') + '.' +
                                       day.strftime('%d') + '/')
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

    def urls_in_date_range(self, t_start: date, t_end: date, suffix: str = "") -> list[str]:
        """
        Return the url of every file from a granule from between start and end dates (inclusive). Higher than daily
        (e.g., hourly) precision for start/end times is not available.

        :param t_start: Start date.
        :param t_end: End date.
        :param suffix: Only yield urls ending in this string.
        :return: List of file urls in the prescribed range.
        """
        urls = []
        delta = t_end - t_start
        for nd in range(delta.days + 1):
            day = t_start + timedelta(days=nd)
            # TODO: code duplication from download_time_series()
            dayurl = urllib.parse.urljoin(self._BASE_URL, day.strftime('%Y') + '.' + day.strftime('%m') + '.' +
                                          day.strftime('%d') + '/')
            urls += [dayurl + file for file in self.retrieve_links(dayurl, suffix)]
        return urls


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

