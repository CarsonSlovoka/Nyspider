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
from common.Crawler import _CrawlerInterface, _SeleniumRunner

from Carson.Class.Logging import CLogging  # pip install carson-logging


BACKGROUND_MODE = False


class RentHouse591URL(_SeleniumRunner):
    __slots__ = []

    CSV_TITLE = ['city', 'URL', ]

    def __init__(self, log_path):
        super().__init__(Website.RENT_591, log_path, BACKGROUND_MODE)
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
            n_data_count = 0
            next_city_flag: bool = True
            while next_city_flag:
                cur_tag_city = self._search(cur_city_name)
                webdriver.ActionChains(self.web).move_to_element(cur_tag_city).click(cur_tag_city).perform()
                # self.web.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                tag_content = self.web.find_element_by_id('content')

                content_html = tag_content.get_attribute('innerHTML')
                filter_data = SoupStrainer(['h3', ])
                parser_html = BeautifulSoup(content_html, 'lxml', parse_only=filter_data)
                result_set_a = parser_html.findAll('a', attrs={'style': [''], })
                for cur_a in result_set_a:
                    n_data_count += 1
                    self.write([cur_city_name, cur_a.attrs.get('href', "")])

                    if n_data_count > 30:
                        next_city_flag = False
                        break

                while next_city_flag:
                    try:
                        tag_next = self.web.find_element_by_class_name('pageNext')  # pageNext last
                        webdriver.ActionChains(self.web).move_to_element(tag_next).click(tag_next).perform()
                        break
                    except NoSuchElementException:
                        print(f'{cur_city_name:<10} cost time:{green_text(str(time() - t_s))}')
                        next_city_flag = False
                        break
                    except StaleElementReferenceException:  # retry until successful
                        highlight_print('StaleElementReferenceException')
                        sleep(3)
                        self.web.refresh()
                        continue

                if not next_city_flag:
                    print(f'{cur_city_name:<10} cost time:{green_text(str(time() - t_s))}')
                    break


class RenHouse591Info(_CrawlerInterface):
    __slots__ = ['_url', ]

    OUT_DIR = 'output/url_data'

    CSV_TITLE = dict(provider_name='出租者',  # div class="infoOne clearfix" find i
                     provider_type='出租者身份',  # div class="infoOne clearfix" find i .text
                     phone='聯絡電話',  # span class="num" img=src <--download and recognize
                     house_type='型態',  # div class="detailInfo clearfix" -> find ul class="attr" -> find_elements('li')[3]
                     state='現況',  # div class="detailInfo clearfix" -> find ul class="attr" -> find_elements('li')[4]
                     gender='性別')

    """
    '男' if provider_name in ('先生', '帥哥') else 
        '女' if provider_name in ('小姐', '女士', '美女') else '用ML從照片判別姓別'
    """

    async def get_response(self, *args) -> list:
        pass

    def parser_html(self, *args):
        pass

    def run(self, *args) -> None:
        pass

    async def write(self, *args) -> bool:
        pass


def main(args):
    parser = RentHouse591URL(Path('temp.temp'))
    parser.start(args.city_name_tuple)


if __name__ == '__main__':
    from argparse import ArgumentParser, RawTextHelpFormatter
    from configparser import ConfigParser, ExtendedInterpolation

    config = ConfigParser(interpolation=ExtendedInterpolation())  # ConfigParser will see all the variable its type as "str"
    read_config_result = config.read(['config.ini', ], encoding='utf-8')

    obj_ini = InIGetter(Path('config.ini'))
    arg_parser = ArgumentParser(usage="", formatter_class=RawTextHelpFormatter)

    arg_parser.add_argument("city_name_tuple", help=f'such as: ("新北市", "台北市")', nargs='?', default=obj_ini.get('city_name_tuple'))
    g_args = arg_parser.parse_args()

    if 'CHECK POSITIONAL ARGUMENTS':
        for attr_name, value in vars(g_args).items():
            if attr_name.startswith('-') or value is not None:  # Required Value must not None.
                continue
            print(f'error required values of {highlight_print(attr_name, print_flag=False)} is None')
            exit(-1)

    if 'ENSURE TYPE':
        g_args.city_name_tuple = eval(g_args.city_name_tuple)

    if highlight_print('INPUT PARAMETER'):  # Show input parameter let use knows.
        print(f"{'key':<20} {'value':<40}")
        for _key, _value in vars(g_args).items():
            print(f"{_key:<20} {str(_value) if _value is not None else '':<40}")
    main(g_args)
