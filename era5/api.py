import os
import sys
import re
import calendar
from urllib.request import build_opener
from datetime import datetime, timedelta, date
from typing import List

import requests
from bs4 import BeautifulSoup


class BaseAPI:
    def __init__(self):
        self._base_url = None

    def get_page_links(self, page_url: str) -> List[str]:
        print(page_url)
        request = requests.get(page_url)
        soup = BeautifulSoup(request.text, 'html.parser')
        year_paths = []
        print([link["href"] for link in soup.find_all("a", href=True)])
        return [link["href"] for link in soup.find_all("a", href=True)]

    @staticmethod
    def get_end_of_month(year, month) -> datetime:
        days_in_month = calendar.monthrange(year, month)[1]
        last_day = date(year, month, days_in_month)
        return datetime(last_day.year, last_day.month, last_day.day, 23, 59, 59)


class HourlySingleLevelInstantaneous(BaseAPI):
    def __init__(self):
        super().__init__()
        self._dataset_url = 'files/g/ds633.0/e5.oper.fc.sfc.instan/'
        self._base_url = 'https://thredds.rda.ucar.edu/thredds/catalog/' + self._dataset_url
        self.download_url = 'https://stratus.rda.ucar.edu/ds633.0/e5.oper.an.sfc/'
        self._directory_re = r'(?P<year>\d{4})(?P<month>\d{2})'
        self._file_re = r'e5\.oper\.fc\.sfc\.instan\.(?P<n1>\d{3})\_(?P<n2>\d{3})\_(?P<var>\w+)\.(?P<n3>\w+)\.(?P<start_date>\d{10})\_(?P<end_date>\d{10})\.nc$'

    def get_available_file_links(self, start_date: str, end_date: str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d') - timedelta(hours=1)
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        directories_in_range = []
        for directory_link in [link.replace('/catalog.html', "") for link in
                               self.get_page_links(self._base_url + 'catalog.html')]:
            match = re.match(self._directory_re, directory_link)
            if match:
                group_dict = match.groupdict()
                year = int(group_dict['year'])
                month = int(group_dict['month'])

                if start_date <= self.get_end_of_month(year, month) and datetime(year, month, 1) <= end_date:
                    directories_in_range.append(directory_link)

        file_links = []
        for directory_link in directories_in_range:
            for file in [link.replace('catalog.html?dataset=' + self._dataset_url + directory_link + '/', "") for
                         link in self.get_page_links(self._base_url + directory_link + '/catalog.html')]:
                print(file)
                match = re.match(self._file_re, file)
                if match:
                    group_dict = match.groupdict()
                    file_start = datetime.strptime(group_dict['start_date'], "%Y%m%d%H")
                    file_end = datetime.strptime(group_dict['end_date'], "%Y%m%d%H")
                    print(file_start, file_end)
                    if start_date <= file_end and end_date >= file_start:
                        file_links.append(self.download_url + '/' + directory_link + '/' + file)

        return file_links

    def download(self, start_date: str, end_date: str):
        file_links = self.get_available_file_links(start_date, end_date)
        print(file_links)
        # opener = build_opener()
        #
        # for file in file_links:
        #     ofile = os.path.basename(file)
        #     sys.stdout.write("downloading " + ofile + " ... ")
        #     sys.stdout.flush()
        #     infile = opener.open(file)
        #     outfile = open(ofile, "wb")
        #     outfile.write(infile.read())
        #     outfile.close()
        #     sys.stdout.write("done\n")
