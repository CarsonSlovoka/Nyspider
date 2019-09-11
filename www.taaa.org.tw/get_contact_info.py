# coding:utf-8
from bs4 import BeautifulSoup, SoupStrainer
import requests
import time

import abc
import typing
import traceback

from Carson.Class.Logging import CLogging  # pip install carson-logging


class _SpiderBase(abc.ABC):
    def __init__(self, log_name):
        __slot__ = ['session', 'log', 'headers', '_work_list']
        self.session = requests.session()
        self._log = CLogging("logger_name", f'{log_name}.txt')
        self.log = self._log.info
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': "1",
            'Connection': 'keep-alive'}
        self._work_list = []

    @property
    def work_list(self):
        return self._work_list

    def set_work_list(self, data_list: typing.List[typing.Tuple]):
        """

        :param data_list: [(query_url,  total_page), (query_url2,  total_page2) ...]
        :return:
        """

        self._work_list = data_list

    def run(self):
        for query_url, total_page in self.work_list:
            for cur_page in range(total_page):
                try:
                    lists = self.spider(cur_page, query_url)
                    self.write(lists)
                except Exception as e:
                    print(traceback.format_exc())
                    print(str(e))
        self._log.close()

    @abc.abstractmethod
    def spider(self, page, name) -> list:
        return []

    @abc.abstractmethod
    def write(self, list_data: list):
        pass


class TAAA(_SpiderBase):  # TAIPEI ASSOCIATION OF ADVERTISING AGENCIES
    """
        function crate date: 2019/09/03
    """
    def __init__(self, log_name='TAAA'):
        super().__init__(log_name)

    def write(self, lists):
        if len(lists) > 0:
            self.log('\t'.join(lists).replace('\r\n', ' '))  # output extension: csv, sep="\t"

    def spider(self, page, name) -> list:
        lists = []
        url = f'http://www.taaa.org.tw/company/{page}'
        server_response = requests.get(url, headers=self.headers)
        if server_response.status_code != 200:
            print(f'error to connect:{url}')
            return []

        filter_data = SoupStrainer('div', attrs={'class': ['sider-info']})
        parsed_slide_info = BeautifulSoup(server_response.text, 'lxml', parse_only=filter_data)
        if parsed_slide_info is None:
            return []

        contact_info = parsed_slide_info.find('div', attrs={'class': ['info']})
        # contact_info.find('p', string=self.query_list[idx]).find_next_siblings()
        if contact_info is None:
            print(f'parse error. msg: no slide info. url: {url}')
            return []

        p_datas = contact_info.findAll('p')  # contact_info.find('p').find_next_siblings()
        dict_record = dict(add="", tel="", fax="", email="", site="")
        for p in p_datas:
            key_name = p.attrs['class'][0]
            if key_name in dict_record:
                text = p.text
                for ignore_text in ('電話：', '傳真：', 'E-mail：', '網站：'):
                    if text.find(ignore_text) != -1:
                        text = text.replace(ignore_text, "")
                        break  # There can be only one
                dict_record[key_name] = text
        contact_info_list = [e for e in dict_record.values()]

        filter_data = SoupStrainer('h3', attrs={'class': ['page-title']})
        parsed_company_name = BeautifulSoup(server_response.text, 'lxml', parse_only=filter_data)
        company_name = parsed_company_name.text if parsed_company_name else ""
        lists = [url, company_name]
        lists.extend(contact_info_list)
        return lists


def main():
    for cur_spider, work_list in [(TAAA, [(None, 201)]), ]:
        obj = cur_spider()
        if not isinstance(obj, _SpiderBase):
            continue
        obj.set_work_list(work_list)
        obj.run()
        print(f'{obj.__name__} OK')


if __name__ == '__main__':
    main()
