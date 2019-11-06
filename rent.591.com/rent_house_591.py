"""
prepared:
    1. chromedriver.exe: download from https://chromedriver.chromium.org/downloads
    #. put ``chromedriver.exe`` to {executable}/Scripts/

USAGE::

"""
from os import path, startfile
from pathlib import Path
from sys import executable

import abc
from time import sleep

from bs4 import BeautifulSoup, SoupStrainer

from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException


from compat import *
from common.structured import *

from Carson.Class.Logging import CLogging  # pip install carson-logging


BACKGROUND_MODE = True


class WebParser(abc.ABC):
    __slots__ = ['_web', '_log']

    BACKGROUND_MODE: bool = BACKGROUND_MODE

    def __init__(self, url: URL, log_path: Path = None):
        self._web = self._open_url(url)
        self._log = CLogging("log_name", log_path) if log_path else None

    def write(self, list_msg: list, sep='\t'):
        if self._log is None:
            return
        self._log.info(sep.join(list_msg))

    @property
    def web(self):
        return self._web

    def _open_url(self, url: URL) -> webdriver:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option("detach", True)  # It still exists when the program ends.
        chrome_options.add_argument("--start-maximized") if not self.BACKGROUND_MODE else None
        chrome_options.add_argument("headless") if self.BACKGROUND_MODE else None
        # chrome_options.add_argument('window-size=2560,1440')
        chrome_driver_exe_path = Path(executable).parent.joinpath('Scripts/chromedriver.exe').resolve()
        assert chrome_driver_exe_path.exists(), 'chromedriver.exe not found!'
        web = webdriver.Chrome(executable_path=str(chrome_driver_exe_path), options=chrome_options)
        web.set_window_position(-9999, 0) if self.BACKGROUND_MODE else None
        web.implicitly_wait(3)  # global setting ``maximum wait time``
        web.get(str(url))
        return web

    @abc.abstractmethod
    def _search(self, *args):
        ...


class RentHouse591(WebParser):
    __slots__ = []

    """
    CSV_TITLE = dict(provider_name='出租者',  # div class="infoOne clearfix" find i
                     provider_type='出租者身份',  # div class="infoOne clearfix" find i .text
                     phone='聯絡電話',  # span class="num" img=src <--download and recognize
                     house_type='型態',  # div class="detailInfo clearfix" -> find ul class="attr" -> find_elements('li')[3]
                     state='現況',  # div class="detailInfo clearfix" -> find ul class="attr" -> find_elements('li')[4]
                     gender='性別')
    """

    """
    '男' if provider_name in ('先生', '帥哥') else 
        '女' if provider_name in ('小姐', '女士', '美女') else '用ML從照片判別姓別'
    """

    CSV_TITLE = ['city', 'URL', ]

    def __init__(self, log_path):
        super().__init__(Website.RENT_591, log_path)
        self.write(self.CSV_TITLE)  # csv title

    def _search(self, city_name: str) -> WebElement:
        location = self.web.find_element_by_class_name('search-location-span')
        location.click()
        tag_ul = self.web.find_element_by_id('optionBox')
        tag_city_list = tag_ul.find_elements_by_tag_name('li')
        dict_search = {tag_city.text: tag_city for tag_city in tag_city_list}
        return dict_search.get(city_name)

    def start(self, city_tuple: tuple):
        area_box_close = self.web.find_element_by_id('area-box-close')
        area_box_close.click()

        for cur_city_name in city_tuple:
            t_s = time()
            while 1:
                cur_tag_city = self._search(cur_city_name)
                webdriver.ActionChains(self.web).move_to_element(cur_tag_city).click(cur_tag_city).perform()
                # self.web.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                tag_content = self.web.find_element_by_id('content')

                content_html = tag_content.get_attribute('innerHTML')
                filter_data = SoupStrainer(['h3', ])
                parser_html = BeautifulSoup(content_html, 'lxml', parse_only=filter_data)
                result_set_a = parser_html.findAll('a', attrs={'style': [''], })
                for cur_a in result_set_a:
                    self.write([cur_city_name, cur_a.attrs.get('href', "")])

                next_city_flag = False
                while 1:
                    try:
                        tag_next = self.web.find_element_by_class_name('pageNext')  # pageNext last
                        webdriver.ActionChains(self.web).move_to_element(tag_next).click(tag_next).perform()
                        break
                    except NoSuchElementException:
                        print(f'{cur_city_name:<10} cost time:{green_text(str(time() - t_s))}')
                        next_city_flag = True  # next city
                        break
                    except StaleElementReferenceException:
                        highlight_print('StaleElementReferenceException')
                        sleep(3)
                        self.web.refresh()
                        continue
                if next_city_flag:
                    print(f'{cur_city_name:<10} cost time:{green_text(str(time() - t_s))}')
                    break


def main():
    parser = RentHouse591(Path('temp.temp'))
    parser.start(('新北市', '台北市', ))


if __name__ == '__main__':
    main()
