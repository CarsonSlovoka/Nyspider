from carson_spider.api.spider import SpiderBase
from carson_spider.api.utils import LogMixin

from bs4 import BeautifulSoup, SoupStrainer, ResultSet, Tag
import requests
from carson_spider.api.utils import LogMixin
from carson_spider.api.spider import SpiderBase

from typing import List, Tuple, Dict, Iterator
from pathlib import Path
import traceback
import sys

import aiohttp
import asyncio
from asyncio import Task
import aiofiles

import numpy as np
import pandas as pd
import numpy as np


class Kanji(SpiderBase, LogMixin):  # https://kanji.jitenon.jp/cat/joyo.html
    """
        function crate date: 2020/09/29
    """

    __slots__ = ('_log', 'target_file_path', 'output_path')
    URL_ROOT = 'https://kanji.jitenon.jp'

    MAX_QUEUE_URL_SIZE = 60
    MAX_PARSER = 20

    def __init__(self, target_file_path: Path):
        super().__init__()
        output_path = Path(f'./output/csv/{Path(__file__).stem}.csv')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path = output_path
        need_write_header = False if self.output_path.exists() else True
        self._log = self.new_logger(self.__class__.__name__, output_path=output_path, mode='r')
        if need_write_header:
            self.log(['URL',
                      'Unicode', 'JIS水準', '漢検級', '学年',
                      '部首', '画数', '種別',
                      '音読み', '訓読み', '意味',
                      '明朝体', '教科書体', '教科書体（筆順）'])  # write title
        self.target_file_path = target_file_path

    def work_list(self) -> Iterator[str]:
        try:
            df = pd.read_csv(self.output_path, usecols=['URL'], sep=self.SEP)
        except ValueError as e:
            sys.stderr.write(f'Error. read file:{self.output_path}:\n {e}')
            return
        with open(self.target_file_path, 'r', encoding='utf-8') as f:
            f.readline()  # skip title line
            for line in f:
                url, *_ = line.split('\n')
                if url in df.URL.values.tolist():
                    print(f'We have done it before. {url:<66}')
                    continue
                yield url

    def write(self, dict_data: Dict):
        if len(dict_data) == 0:
            return
        row_data = []
        for key in ('Unicode', 'JIS水準', '漢検級', '学年', '部首', '画数', '種別', '音読み', '訓読み', '意味', 'img_info'):
            if key == 'img_info':
                dict_img_info: Dict = dict_data[key]
                for name in ('明朝体', '教科書体', '教科書体（筆順）'):
                    row_data.append(dict_img_info.get(name, ''))
            else:
                row_data.append(dict_data.get(key, ''))
        self.log(row_data)

    def spider(self, query_url: str) -> Dict:
        ...

    async def async_spider(self, query_url: str) -> Dict:
        try:
            async with aiohttp.ClientSession() as session:
                dict_delay = {'delay': str(np.random.choice(
                    [0, 1, 2, 3], size=1,
                    p=[0.1, 0.25, 0.25, 0.4]
                )[0])}  # Some responses will have zero delay, and some will have maximum of 3 seconds delay.
                header = {**self.headers, **dict_delay}
                async with session.get(query_url, timeout=10, headers=header) as server_response:
                    if server_response.status != 200:
                        sys.stderr.write(f'error to connect:{query_url}')
                        return {}

                    html_bytes: bytes = await server_response.read()
                    html_text: str = html_bytes.decode('utf-8')
                    return self.spider_base(html_text)  # asyncio.TimeoutError
        except asyncio.TimeoutError as e:
            sys.stderr.write(f'error to connect {e!r}: {query_url}')
            return {}

    def spider_base(self, html_text: str, sep='|') -> Dict:
        filter_data = SoupStrainer('div', attrs={'class': ['kanji_main ChangeElem_Panel', 'normal_box', 'kanji_right']})
        bs = BeautifulSoup(html_text, 'lxml', parse_only=filter_data)

        if bs is None:
            return {}

        dict_normal_box = {'Unicode': '', 'JIS水準': '', '漢検級': '', '学年': ''}
        try:
            tag_box: Tag = bs.find('div', attrs={'class': ['normal_box']})
            set_dl: ResultSet = tag_box.findAll('dl')
            for dl in set_dl:
                name: Tag = dl.find('dt')
                value: Tag = dl.find('dd')
                dict_normal_box[name.text] = value.text
            if 'Unicode' in dict_normal_box:
                dict_normal_box['Unicode'] = dict_normal_box['Unicode'][2:]  # U+4E00 -> 4E00
        except:
            print(traceback.format_exc())
            raise RuntimeError

        dict_info = {'部首': '', '画数': '', '種別': ''}
        tag_right: Tag = bs.find('div', attrs={'class': ['kanji_right']})
        try:
            div_tag_kan: Tag = tag_right.find('div', attrs={'class': ['kan_list']})
            set_dl: ResultSet = div_tag_kan.findAll('dl')
            for dl in set_dl:
                dl: Tag
                name = dl.find('dt').text
                value_list = []
                for a in dl.find('dd').findAll('a'):
                    value_list.append(a.text)
                dict_info[name] = sep.join(value_list)
        except:
            print(traceback.format_exc())
            raise RuntimeError

        dict_info2 = {'音読み': '', '訓読み': '', '意味': ''}
        try:
            tag_table: Tag = tag_right.find('table', attrs={'class': ['kanjirighttb']})
            set_tr: ResultSet = tag_table.findAll('tr')
            for cur_idx, tr in enumerate(set_tr):
                tag_th: Tag = tr.find('th')
                if tag_th:
                    val_list = []
                    name = tag_th.text
                    val_list.append(tr.find('td').find('a').text if name != '意味' else tr.find('td').text)

                    if tag_th.attrs.get('rowspan'):
                        max_idx = int(tag_th.attrs['rowspan']) + cur_idx
                        for idx in range(cur_idx + 1, max_idx):
                            tr: Tag = set_tr[idx]
                            val_list.append(tr.find('td').find('a').text if name != '意味' else tr.find('td').text)

                    dict_info2[name] = sep.join(
                        [_.replace(self.SEP, '    ') if self.SEP in _ else _ for _ in val_list]
                    )
        except:
            print(traceback.format_exc())
            raise RuntimeError

        set_a: ResultSet = bs.findAll('a', attrs={'data-lightbox': ['bigimg']})
        dict_img_info = {'img_info': dict()}
        for tag_a in set_a:
            url_img = tag_a.attrs['href']  # '../shotai3/001.gif'
            url_img = self.URL_ROOT + url_img[2:]
            name = tag_a.attrs['data-title']  # 明朝体, 教科書体, 教科書体（筆順）
            dict_img_info['img_info'][name] = url_img
        dict_result = dict(**dict_normal_box, **dict_info, **dict_info2, **dict_img_info)
        return dict_result

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
                    dict_data = await self.async_spider(query_url)
                    if dict_data:
                        dict_data = dict(url=query_url, **dict_data)
                        q_data.put_nowait(dict_data)
                except Exception as e:
                    # print(traceback.format_exc())
                    from console_color import cprint, RGB
                    # Cannot connect to host kanji.jitenon.jp:443 ssl:default [getaddrinfo failed]
                    cprint(str(e), RGB.RED, RGB.YELLOW)

        async def async_write(dict_data: Dict):
            if len(dict_data) == 0:
                return
            row_data = []
            for key in ('url', 'Unicode', 'JIS水準', '漢検級', '学年', '部首', '画数', '種別', '音読み', '訓読み', '意味', 'img_info'):
                if key == 'img_info':
                    dict_img_info: Dict = dict_data[key]
                    for name in ('明朝体', '教科書体', '教科書体（筆順）'):
                        row_data.append(dict_img_info.get(name, ''))
                else:
                    row_data.append(dict_data.get(key, ''))

            async with aiofiles.open(self.output_path, 'a', encoding='utf-8') as f:
                await f.write(self.SEP.join(row_data) + '\n')

        async def url_center(q: asyncio.Queue):
            for idx, query_url in enumerate(self.work_list()):
                print(f'{idx + 1:<10} put url: {query_url}')
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
                dict_data: Dict = await q_data.get()
                n_data_get += 1
                print(f'{"get the data":30} {n_data_get:<10}')
                try:
                    await async_write(dict_data)
                except Exception as e:
                    print(traceback.format_exc())
                    print(str(e))

        queue_url = asyncio.Queue(maxsize=self.MAX_QUEUE_URL_SIZE)  # q.put q.put ..., maxsize=20,  # https://www.cnblogs.com/paulwhw/articles/10723887.html
        queue_data = asyncio.Queue()
        loop = asyncio.get_event_loop()
        task_url: Task = loop.create_task(url_center(queue_url))
        list_task_parser: List[Task] = []
        for i in range(self.MAX_PARSER):
            # "50".zfill(4) => 0050
            list_task_parser.append(loop.create_task(handler(f'handler{str(i).zfill(3)}', task_url, queue_url, queue_data)))
        task_writer: Task = loop.create_task(data_center(list_task_parser, queue_data))
        task_list: List = [task_url, task_writer]
        task_list.extend(list_task_parser)
        try:  # = asyncio.run(task_list)
            loop.run_until_complete(asyncio.wait(task_list))
        finally:
            asyncio.set_event_loop(None)
            loop.close()


def main():
    Kanji(target_file_path=Path('./output/csv/target_url.csv')).run()


if __name__ == '__main__':
    main()
