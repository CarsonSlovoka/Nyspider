import requests  # to get image from the web
import shutil  # to save it locally
from carson_spider.api.spider import SpiderBase
from carson_spider.api.utils import LogMixin
from pathlib import Path
import sys

import asyncio
from asyncio import Task
import aiohttp
import aiofiles  # pip install aiohttp -> pip install aiofiles

import traceback
from typing import List, Tuple, Iterator

import pandas as pd


def test_download_image():
    image_url = "https://kanji.jitenon.jp/shotai2/838.gif"
    filename = image_url.split("/")[-1]

    r = requests.get(image_url, stream=True)

    if r.status_code == 200:
        # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
        r.raw.decode_content = True
        with open(filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)


class Kanji(SpiderBase, LogMixin):  # https://kanji.jitenon.jp/cat/joyo.html
    """
        function crate date: 2020/09/29
    """

    __slots__ = ('_log', 'target_file_path', 'output_path')
    URL_ROOT = 'https://kanji.jitenon.jp'

    MAX_QUEUE_URL_SIZE = 20
    MAX_PARSER = 5
    TIMEOUT = 15

    def __init__(self, target_file_path: Path):
        super().__init__()
        output_path = Path(f'./output/csv/{Path(__file__).stem}.csv')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path = output_path
        need_write_title = False if self.output_path.exists() else True
        self._log = self.new_logger(self.__class__.__name__, output_path=output_path, mode='a')
        if need_write_title:
            self.log(['name', 'url_img', 'utf16be_str'])  # write title
        self.target_file_path = target_file_path

    def work_list(self) -> Iterator[Tuple[str, str, str]]:
        df = pd.read_csv(self.output_path, usecols=['url_img'], sep=self.SEP)
        with open(self.target_file_path, 'r', encoding='utf-8') as f:
            f.readline()  # skip title line
            for line in f:
                output_folder_name, img_url, utf16be_str, *_ = line.split(self.SEP)
                if img_url in df.url_img.tolist():
                    # We have been downloaded before.
                    print(f'We have been downloaded before. {img_url:<66}')
                    continue
                yield output_folder_name, img_url, utf16be_str

    def run(self):
        async def handler(name: str, task_source: Task, q_url: asyncio.Queue, q_data: asyncio.Queue):
            n_job_get = 0
            while 1:
                if q_url.empty() and getattr(task_source, '_result') == 'FINISHED':
                    return 'FINISHED'
                output_folder_name, img_url, utf16be_str = await q_url.get()
                n_job_get += 1
                print(f'{name} {n_job_get:<10} download url: {img_url}')
                try:
                    img_bytes: bytes = await self.async_spider(img_url)
                    q_data.put_nowait([output_folder_name, img_url, utf16be_str, img_bytes])
                except Exception as e:
                    print(traceback.format_exc())
                    print(str(e))

        async def async_write(list_data: List):
            list_data = [str(_).strip() for _ in list_data]
            async with aiofiles.open(self.output_path, 'a', encoding='utf-8') as f:
                await f.write(self.SEP.join(list_data) + '\n')

        async def url_center(q: asyncio.Queue):
            for idx, query_data in enumerate(self.work_list()):
                print(f'{idx + 1:<10} put data: {query_data}')
                await q.put(query_data)
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
                output_folder_name, img_url, utf16be_str, img_bytes = data_list

                if len(img_bytes) == 0:
                    # Now, we can know it's successful for every data that has been written.
                    continue

                output_dir = Path('./output/image') / Path(output_folder_name)
                if not output_dir.exists():
                    output_dir.mkdir(parents=True, exist_ok=True)
                output_image_file = output_dir / Path(utf16be_str.strip() + Path(img_url).suffix)

                async with aiofiles.open(output_image_file, 'wb') as f:
                    await f.write(img_bytes)

                n_data_get += 1
                print(f'{"get the data":30} {n_data_get:<10}')
                try:
                    data_list = data_list[:-1]
                    await async_write(data_list)
                except Exception as e:
                    print(traceback.format_exc())
                    print(str(e))

        loop = asyncio.get_event_loop()
        queue_url = asyncio.Queue(self.MAX_QUEUE_URL_SIZE)  # q.put q.put ..., maxsize=20,  # https://www.cnblogs.com/paulwhw/articles/10723887.html
        queue_data = asyncio.Queue()

        task_url: Task = loop.create_task(url_center(queue_url))

        max_parser = self.MAX_PARSER
        list_task_parser: List[Task] = []
        for i in range(max_parser):
            # "50".zfill(4) => 0050
            list_task_parser.append(loop.create_task(handler(f'handler{str(i).zfill(3)}', task_url, queue_url, queue_data)))

        task_writer: Task = loop.create_task(data_center(list_task_parser, queue_data))

        task_list: List = [task_url, task_writer]
        task_list.extend(list_task_parser)

        loop.run_until_complete(asyncio.wait(task_list))

    async def async_spider(self, img_url: str) -> bytes:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(img_url, timeout=self.TIMEOUT, headers=self.headers) as server_response:
                    if server_response.status != 200:
                        sys.stderr.write(f'error to connect:{img_url}')
                        return b''

                    html_bytes: bytes = await server_response.read()
                    # html_text: str = html_bytes.decode('utf-8')
                    return html_bytes
            except Exception as e:  # TimeoutError
                sys.stderr.write(f'error to connect {e!r}: {img_url}')
                return b''

    def spider(self, *args, **kwargs) -> list:
        ...

    def write(self, list_data: list):
        ...


def main():
    Kanji(target_file_path=Path('./output/csv/get_img_url_from_target_url.csv')).run()


if __name__ == '__main__':
    main()
