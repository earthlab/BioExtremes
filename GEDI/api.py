"""
This module contains implements APIs to access GEDI L1B, L2B, and L2A data. Note that the only way to access the
contents of a GEDI archive file is through the process_in_memory_file() method of the base GEDI class. This is to
discourage writing unprocessed files to disk, since the raw data is large and mostly not useful.
"""

import os
from io import BytesIO
from urllib.error import HTTPError

import certifi
import requests
from typing import List, Tuple, Callable, Iterator
from http.cookiejar import CookieJar
import getpass
import re
from datetime import datetime, timedelta, date
import urllib
from bs4 import BeautifulSoup


class GEDIAPI:
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

        # resolve potential issue with SSL certs
        ssl_cert_path = certifi.where()
        if 'SSL_CERT_FILE' not in os.environ or os.environ['SSL_CERT_FILE'] != ssl_cert_path:
            os.environ['SSL_CERT_FILE'] = ssl_cert_path
        if 'REQUESTS_CA_BUNDLE' not in os.environ or os.environ['REQUESTS_CA_BUNDLE'] != ssl_cert_path:
            os.environ['REQUESTS_CA_BUNDLE'] = ssl_cert_path

    def check_credentials(self):
        """Will raise a permissions error if unable to download."""
        try:
            self.process_in_memory_file(
                "https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/GEDI02_A_2020146010156_O08211_03_T02527_02_003_01_V002.h5.xml",
                lambda _: True
            )
        except HTTPError as e:
            print('An HTTPError occurred, suggesting that your authentication may have failed. \
                    Are your credentials correct?')
            raise e

    def _request_raw_data(self, link: str):
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
        return urllib.request.urlopen(myrequest)

    def process_in_memory_file(self, link: str, func: Callable, *args, **kwargs):
        """
        Perform an action on the contents of a webpage while storing them in a memory file in RAM.

        :param link: webpage url
        :param func: Method which takes a file-like object as its first argument and performs the action.
        :param args: Passed to func.
        :param kwargs: Passed to func.
        :return: Result of func([linked file], *args, **kwargs), or None if a memory error occurs.
        """
        response = self._request_raw_data(link)
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
            except Exception as e:
                print(f"An Exception of type {type(e)} caused failed download from {link}")
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

    def urls_in_date_range(self, t_start: date, t_end: date, suffix: str = "") -> Iterator[str]:
        """
        Yields the url of every file from a granule from between start and end dates (inclusive). Higher than daily
        (e.g., hourly) precision for start/end times is not available.

        :param t_start: Start date.
        :param t_end: End date.
        :param suffix: Only yield urls ending in this string.
        """
        delta = t_end - t_start
        for nd in range(delta.days + 1):
            day = t_start + timedelta(days=nd)
            # TODO: code duplication from download_time_series()
            dayurl = urllib.parse.urljoin(self._BASE_URL, day.strftime('%Y') + '.' + day.strftime('%m') + '.' +
                                          day.strftime('%d') + '/')
            yield from (dayurl + file for file in self.retrieve_links(dayurl, suffix))


class L2AAPI(GEDIAPI):
    _BASE_URL = 'https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/'

    def __init__(self, lazy: bool = False):
        super().__init__(lazy=lazy)
        self._file_re = r"GEDI02_A" + self._BASE_FILE_RE
        self._dates = self._retrieve_dates(self._BASE_URL)


class L2BAPI(GEDIAPI):
    _BASE_URL = 'https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_B.002/'

    def __init__(self, lazy: bool = False):
        super().__init__(lazy=lazy)
        self._file_re = r"GEDI02_B" + self._BASE_FILE_RE
        self._dates = self._retrieve_dates(self._BASE_URL)


class L1BAPI(GEDIAPI):
    _BASE_URL = 'https://e4ftl01.cr.usgs.gov/GEDI/GEDI01_B.002/'

    def __init__(self, lazy: bool = False):
        super().__init__(lazy=lazy)
        self._file_re = r"GEDI01_B" + self._BASE_FILE_RE
        self._dates = self._retrieve_dates(self._BASE_URL)

