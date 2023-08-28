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


class BaseAPI:
    """
    Defines all the attributes and methods common to the child APIs.
    """

    def __init__(self, lazy: bool = False):
        """
        Initializes the common attributes required for each data type's API
        """
        self._username = os.environ.get('BEX_USER', None)
        self._password = os.environ.get('BEX_PWD', None)
        self._core_count = os.cpu_count()
        if not lazy:
            pass
            # self._configure()
        self._file_re = None
        self._tif_re = None

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

    def download_time_series(self, queries: List[Tuple[str, str]], outdir: str):
        """
        Attempts to create download requests for each query, if that fails then makes each request in series.
        Args:
            queries (list): List of tuples containing the remote and local locations for each request
        Returns:
            outdir (str): Path to the output file directory
        """
        # From earthlab firedpy package
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


class ForestHeight(BaseAPI):
    _BASE_URL = 'https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/'

    def __init__(self, lazy: bool = False):
        super().__init__(lazy=lazy)
        self._file_re = r"GEDI02_A_(?P<year>\d{4})(?P<doy>\d{3})(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})_O(?P<orbit>\d+)_(?P<sub_oribt>\d+)_T(?P<track_number>\d+)_(?P<ppds>\d{2})_(?P<pge>\d{3})_(?P<granule>\d{2})_V(?P<version>\d{3})\.h5$"
        self._dates = self._retrieve_dates(self._BASE_URL)

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
        super().download_time_series(queries, outdir)
        return outdir
