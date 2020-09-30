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

import aiohttp
import asyncio
from asyncio import Task
import aiofiles


class Kanji(SpiderBase, LogMixin):  # https://kanji.jitenon.jp/cat/joyo.html
    """
        function crate date: 2020/09/29
    """

    __slots__ = ('_log', 'target_file_path', 'output_path')
    URL_ROOT = 'https://kanji.jitenon.jp'

    def __init__(self, target_file_path: Path):
        super().__init__()
        output_path = Path(f'./output/csv/{Path(__file__).stem}.csv')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path = output_path
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

    async def async_spider(self, query_url: str) -> List[Tuple[str, str, str]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(query_url, timeout=10, headers=self.headers) as server_response:
                if server_response.status != 200:
                    sys.stderr.write(f'error to connect:{query_url}')
                    return []

                html_bytes: bytes = await server_response.read()
                html_text: str = html_bytes.decode('utf-8')

                filter_data = SoupStrainer('div', attrs={'class': ['kanji_main ChangeElem_Panel', 'normal_box']})
                bs = BeautifulSoup(html_text, 'lxml', parse_only=filter_data)
                if bs is None:
                    return []

                list_data = []
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

    def run_old(self):
        for idx, query_url in enumerate(self.work_list()):
            try:
                print(f'{idx:<10}: {query_url}')
                lists = self.spider(query_url)
                self.write(lists)
            except Exception as e:
                print(traceback.format_exc())
                print(str(e))

    def run(self):
        async def handler(name: str, task_source: Task, q_url: asyncio.Queue, q_data: asyncio.Queue):
            n_job_get = 0
            while 1:
                if q_url.empty() and getattr(task_source, '_result') == 'FINISHED':
                    return 'FINISHED'
                query_url = await q_url.get()
                n_job_get += 1
                print(f'{name} {n_job_get:<10} get url: {query_url}')
                try:
                    lists = await self.async_spider(query_url)
                    q_data.put_nowait(lists)
                except Exception as e:
                    print(traceback.format_exc())
                    print(str(e))

        async def async_write(list_data: list):
            async with aiofiles.open(self.output_path, 'a', encoding='utf-8') as f:
                for data in list_data:
                    # name, url_img, utf16be_str = data
                    await f.write(self.SEP.join(data)+'\n')

        async def url_center(q: asyncio.Queue):
            for idx, query_url in enumerate(self.work_list()):
                print(f'{idx+1:<10} put url: {query_url}')
                await q.put(query_url)
            return 'FINISHED'

        async def data_center(list_parser: List[Task], q_data: asyncio.Queue):
            """
            if data in then write it.
            """
            n_data_get = 0
            while 1:
                if q_data.empty():
                    if all(getattr(task_parser, '_result') == 'FINISHED' for task_parser in list_parser):
                        return 'FINISHED'
                data_list: list = await q_data.get()
                n_data_get += 1
                print(f'{"get the data":30} {n_data_get:<10}')
                try:
                    await async_write(data_list)
                except Exception as e:
                    print(traceback.format_exc())
                    print(str(e))

        queue_url = asyncio.Queue(maxsize=20)  # q.put q.put ..., maxsize=20,  # https://www.cnblogs.com/paulwhw/articles/10723887.html
        queue_data = asyncio.Queue()
        loop = asyncio.get_event_loop()
        task_url: Task = loop.create_task(url_center(queue_url))
        max_parser = 10
        list_task_parser: List[Task] = []
        for i in range(max_parser):
            # "50".zfill(4) => 0050
            list_task_parser.append(loop.create_task(handler(f'handler{str(i).zfill(3)}', task_url, queue_url, queue_data)))
        task_writer: Task = loop.create_task(data_center(list_task_parser, queue_data))
        task_list: List = [task_url, task_writer]
        task_list.extend(list_task_parser)
        loop.run_until_complete(asyncio.wait(task_list))


def main():
    Kanji(target_file_path=Path('./output/csv/target_url.csv')).run()


if __name__ == '__main__':
    main()
