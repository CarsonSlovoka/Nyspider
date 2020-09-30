from carson_spider.api.spider import SpiderBase
from carson_spider.api.utils import LogMixin

from bs4 import BeautifulSoup, SoupStrainer, ResultSet, Tag
import requests
from carson_spider.api.utils import LogMixin
from carson_spider.api.spider import SpiderBase

from typing import List, Tuple
from pathlib import Path
import traceback
import sys


class Kanji(SpiderBase, LogMixin):  # https://kanji.jitenon.jp/cat/joyo.html
    """
        function crate date: 2020/09/29
    """

    __slots__ = ('_log', 'target_file_path')
    URL_ROOT = 'https://kanji.jitenon.jp'

    def __init__(self, target_file_path: Path):
        super().__init__()
        output_path = Path(f'./output/csv/{Path(__file__).stem}.csv')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._log = self.new_logger(self.__class__.__name__, output_path=output_path)
        self.log(['name', 'url_img', 'utf16be_str'])  # write title
        self.target_file_path = target_file_path

    def work_list(self):
        with open(self.target_file_path, 'r', encoding='utf-8') as f:
            f.readline()  # skip title line
            for line in f:
                url, *_ = line.split('\n')
                yield url

    def write(self, list_data: list):
        for url_data in list_data:
            # name, url_img, utf16be_str = url_data
            self.log(url_data)

    def spider(self, query_url: str) -> List[Tuple[str, str, str]]:
        list_data = []
        server_response = requests.get(query_url, headers=self.headers)
        if server_response.status_code != 200:
            sys.stderr.write(f'error to connect:{query_url}')
            return []

        filter_data = SoupStrainer('div', attrs={'class': ['kanji_main ChangeElem_Panel', 'normal_box']})
        bs = BeautifulSoup(server_response.text, 'lxml', parse_only=filter_data)
        if bs is None:
            return []

        try:
            tag_box: Tag = bs.find('div', attrs={'class': ['normal_box']})
            tag_dl: Tag = tag_box.find('dl')
            tag_dd: Tag = tag_dl.find('dd')
            str_utf16be = tag_dd.text[2:]  # U+4E00 -> 4E00
        except:
            str_utf16be = '????'

        set_a: ResultSet = bs.findAll('a', attrs={'data-lightbox': ['bigimg']})
        for tag_a in set_a:
            url_img = tag_a.attrs['href']  # '../shotai3/001.gif'
            url_img = self.URL_ROOT + url_img[2:]
            name = tag_a.attrs['data-title']
            list_data.append((name, url_img, str_utf16be))
        return list_data

    def run(self):
        for query_url in self.work_list():
            try:
                lists = self.spider(query_url)
                self.write(lists)
            except Exception as e:
                print(traceback.format_exc())
                print(str(e))


def main():
    Kanji(target_file_path=Path('./output/csv/target_url.csv')).run()


if __name__ == '__main__':
    main()
