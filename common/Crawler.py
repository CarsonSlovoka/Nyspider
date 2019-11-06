import aiohttp
import asyncio

from multiprocessing import Lock

import abc
import traceback

from Carson.Class.Logging import CLogging  # pip install carson-logging

from compat import highlight_print
from common.structured import *

from sys import executable
from pathlib import Path

from exceptions import WriteDataFailed

from selenium.webdriver.remote.webelement import WebElement
from selenium import webdriver


class _CrawlerInterface(abc.ABC):
    __slots__ = []

    @abc.abstractmethod
    async def get_response(self, *args) -> list:  # network (IO)
        pass

    @abc.abstractmethod
    def parser_html(self, *args):  # read data from memory
        pass

    @abc.abstractmethod
    def run(self, *args) -> None:
        pass

    @abc.abstractmethod
    async def write(self, *args) -> bool:  # write to drive (IO)
        pass


class _SpiderBase(_CrawlerInterface):
    __slots__ = ['_log', 'log', '_lock', '_timeout']

    def __init__(self, log_path: Path, lock_log: Lock = None, timeout: int = None):
        file_mode = 'a' if log_path.exists() else 'w'
        self._log = CLogging("logger_name", log_path, mode=file_mode)
        self.log = self._log.info
        self._lock = lock_log
        self._timeout = timeout

    @cached_property
    def lock(self):
        return self._lock

    @cached_property
    def timeout(self):
        return self._timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._log.close()

    @abc.abstractmethod
    def get_works_url_list(self, *args) -> list:
        ...

    async def task(self, url: URL, session: aiohttp.ClientSession) -> None:
        html = await self.get_response(url, session)
        lists = await self.parser_html(url, html) if asyncio.iscoroutinefunction(self.parser_html) else self.parser_html(url, html)
        if len(lists) == 0:
            return
        if self.lock:
            with self.lock:
                result = await self.write(lists)
        else:
            result = await self.write(lists)
        if not result:
            print(traceback.format_exc())
            highlight_print(f'error occur on write url:{url}')
            return

    async def _main(self, url_list, max_threads: int):
        async with aiohttp.ClientSession() as session:
            for cur_url_list in [url_list[i:i + max_threads] for i in range(0, len(url_list), max_threads)]:
                list_task = [asyncio.ensure_future(self.task(cur_url, session)) for cur_url in cur_url_list]
                await asyncio.wait(list_task)

    @abc.abstractmethod
    def run(self, *args, **option):
        loop = asyncio.get_event_loop()
        url_list = self.get_works_url_list(*args)
        loop.run_until_complete(self._main(url_list, option.get('max_threads', 20)))

    async def get_response(self, url: URL, session: aiohttp.ClientSession) -> str:
        async with session.get(url, timeout=self.timeout) as response:
            if response.status != 200:
                return ''
            html = await response.text()  # response.read() bytes
            return html

    @abc.abstractmethod
    def parser_html(self, url: URL, html: str) -> list:
        pass

    @abc.abstractmethod
    async def write(self, lists: list) -> bool:
        try:
            for list_row_data in lists:
                self.log('\t'.join(list_row_data).replace('\r\n', ' '))  # output extension: csv, sep="\t"
            return True
        except WriteDataFailed as e:
            highlight_print(str(e))
            return False


class _SeleniumRunner(abc.ABC):
    __slots__ = ['_web', '_log', ]

    def __init__(self, url: URL, log_path: Path = None, background_mode: bool = True):
        self._web = self._open_url(url, background_mode)
        self._log = CLogging("log_name", log_path) if log_path else None

    def write(self, list_msg: list, sep='\t'):
        if self._log is None:
            return
        self._log.info(sep.join(list_msg))

    @property
    def web(self):
        return self._web

    def _open_url(self, url: URL, background_mode) -> webdriver:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option("detach", True)  # It still exists when the program ends.
        chrome_options.add_argument("--start-maximized") if not background_mode else None
        chrome_options.add_argument("headless") if background_mode else None
        # chrome_options.add_argument('window-size=2560,1440')
        chrome_driver_exe_path = Path(executable).parent.joinpath('Scripts/chromedriver.exe').resolve()
        assert chrome_driver_exe_path.exists(), 'chromedriver.exe not found!'
        web = webdriver.Chrome(executable_path=str(chrome_driver_exe_path), options=chrome_options)
        web.set_window_position(-9999, 0) if background_mode else None
        web.implicitly_wait(3)  # global setting ``maximum wait time``
        web.get(str(url))
        return web

    @abc.abstractmethod
    def _search(self, *args):
        ...
