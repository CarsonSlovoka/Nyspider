from bs4 import BeautifulSoup, SoupStrainer, ResultSet, Tag
import requests
from carson_spider.api.utils import LogMixin
from carson_spider.api.spider import SpiderBase

from typing import List
from pathlib import Path
import traceback


class _SpiderBase(SpiderBase):
    __slots__ = ()

    def run(self):
        try:
            lists = self.spider()
            self.write(lists)
        except Exception as e:
            print(traceback.format_exc())
            print(str(e))

    def spider(self) -> list:
        raise NotImplementedError

    def write(self, list_data: list):
        raise NotImplementedError


class KanjiURL(_SpiderBase, LogMixin):  # https://kanji.jitenon.jp/cat/joyo.html
    """
        function crate date: 2020/09/29
    """

    __slots__ = ('_log',)

    def __init__(self):
        super().__init__()
        output_path = Path(f'./output/csv/target_url.csv')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = self.new_logger(self.__class__.__name__, output_path=output_path)
        self.log(['url'])  # write title

    def write(self, list_data: list):
        for url_data in list_data:
            self.log([url_data])

    def spider(self) -> List[str]:
        list_data = []
        url = f'https://kanji.jitenon.jp/cat/joyo.html'
        server_response = requests.get(url, headers=self.headers)
        if server_response.status_code != 200:
            print(f'error to connect:{url}')
            return []

        filter_data = SoupStrainer('div', attrs={'class': ['parts_data']})
        bs = BeautifulSoup(server_response.text, 'lxml', parse_only=filter_data)
        if bs is None:
            return []

        set_box: ResultSet = bs.findAll('div', attrs={'class': ['parts_box']})
        for div in set_box:
            tag_ul: Tag = div.find('ul', attrs={'class': ['search_parts']})
            set_href: ResultSet = tag_ul.findAll('a')
            for a in set_href:
                list_data.append(a.attrs['href'])
        return list_data


def main():
    KanjiURL().run()


if __name__ == '__main__':
    main()
