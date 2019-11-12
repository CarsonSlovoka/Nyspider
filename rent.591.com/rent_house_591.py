"""
prepared:
    1. chromedriver.exe: download from https://chromedriver.chromium.org/downloads
    #. put ``chromedriver.exe`` to {executable}/Scripts/

USAGE::

"""
from io import StringIO, BytesIO
from os import startfile, cpu_count, environ
from pathlib import Path
from time import sleep

import requests
from bs4 import BeautifulSoup, SoupStrainer, Tag

from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from compat import *
from common.structured import *
from common.Crawler import SpiderBase, SeleniumRunner
from common.Crawler import get_pool, create_spider_and_run


from exceptions import WriteDataFailed

import asyncio

import re
import traceback

from multiprocessing import Lock

from keras.layers.convolutional import Conv2D, MaxPooling2D
from keras.layers.core import Flatten, Dense, Dropout
from keras.models import Sequential

import imageio
import cv2
import numpy as np


BACKGROUND_MODE = True
T_IO = TypeVar('T_IO', StringIO, BytesIO)

environ["TF_CPP_MIN_LOG_LEVEL"] = '3'  # show only Error


def get_letter_image_regions(img) -> list:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh_gray = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)[1]

    contours, hierarchy = cv2.findContours(thresh_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    all_area_set = set()
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        all_area_set.add((x, y, w, h))
    letter_image_regions = sorted(all_area_set, key=lambda e: e[0])
    return letter_image_regions


async def download_and_keep_on_memory(url: URL, headers=None, timeout=None, **option) -> T_IO:
    if headers is None:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Host': 'statics.591.com.tw',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36'
        }
    chunk_size = option.get('chunk_size', 4096)  # default 4KB
    max_size = 1024 ** 2 * option.get('max_size', -1)  # MB, default will ignore.
    response = requests.get(url, headers=headers, timeout=timeout)
    if response.status_code != 200:
        raise requests.ConnectionError(f'{response.status_code}')

    instance_io = StringIO if isinstance(next(response.iter_content(chunk_size=1)), str) else BytesIO
    io_obj = instance_io()
    cur_size = 0
    for chunk in response.iter_content(chunk_size=chunk_size):
        cur_size += chunk_size
        if 0 < max_size < cur_size:
            break
        io_obj.write(chunk)
    io_obj.seek(0)
    return io_obj


class RentHouse591URL(SeleniumRunner):
    __slots__ = []

    CSV_TITLE = ['city', 'URL', ]

    def __init__(self, log_path: Path):
        super().__init__(Website.RENT_591, log_path, BACKGROUND_MODE)
        self.write(self.CSV_TITLE)  # csv title

    def _search(self, city_name: str) -> WebElement:
        location = self.web.find_element_by_class_name('search-location-span')
        location.click()
        tag_ul = self.web.find_element_by_id('optionBox')
        tag_city_list = tag_ul.find_elements_by_tag_name('li')
        dict_search = {tag_city.text: tag_city for tag_city in tag_city_list}
        return dict_search.get(city_name)

    def start(self, city_list: list):
        area_box_close = self.web.find_element_by_id('area-box-close')
        area_box_close.click()

        for cur_city_name in city_list:
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


class RentHouse591Info(SpiderBase):
    __slots__ = ['_model', ]

    OUT_DIR = 'output/url_data'

    CSV_TITLE = dict(provider_name='出租者',  # <div class="infoOne clearfix" find <i
                     gender='性別',
                     provider_type='出租者身份',  # <div class="infoOne clearfix" find <i .text
                     house_type='型態',  # <div class="detailInfo clearfix" -> find <ul class="attr" -> find_elements('li')[3]
                     state='現況',  # <div class="detailInfo clearfix" -> find <ul class="attr" -> find_elements('li')[4]
                     phone='聯絡電話',  # <span class="num" -> <img src=... <--download and recognize
                     URL='URL',
                     )

    def __init__(self, log_path: Path, lock_log: Lock = None, timeout: int = None):
        super().__init__(log_path, lock_log, timeout)

        # build_model
        model = Sequential()
        model.add(Conv2D(20, (5, 5), padding="same", input_shape=(30, 30, 1), activation="relu"))
        model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
        model.add(Conv2D(50, (5, 5), padding="same", activation="relu"))
        model.add(MaxPooling2D(pool_size=(2, 2), strides=(2, 2)))
        model.add(Flatten())
        model.add(Dense(128, activation="relu"))
        model.add(Dropout(0.3))
        model.add(Dense(11, activation="softmax"))
        model.compile(loss="categorical_crossentropy", optimizer="adam", metrics=["accuracy"])
        model.load_weights('rent_591_phone_captcha.h5')
        self._model = model

    @property
    def model(self):
        return self._model

    def get_works_url_list(self, url_list: list) -> list:
        return [('https:' + url).replace(' ', '') for url in url_list]

    @staticmethod
    def get_gender_by_name(name):
        _name = name[-2:]
        return '男' if _name in ('先生', '男士', '帥哥') else \
            '女' if _name in ('小姐', '女士', '美女', '太太') else name  # 'get it from the picture with machine learning'

    async def parser_html(self, url: URL, html_text: str):

        async def get_phone_data(tag_phone_span: Tag) -> str:
            if len(tag_num_span.text) > 9:  # phone number is test
                return [' '.join(e) for e in [re.findall('\\b\\S*\\b', tag_phone_span.text)] if e != ''][0]

            phone_img = tag_phone_span.find('img')
            if phone_img is None:
                highlight_print(f"can't get the phone number. url: {url} (maybe already sold out)")
                return ""
            img_url = phone_img.attrs.get('src')
            io_img = await download_and_keep_on_memory('http:' + img_url if url[0:5] != 'http:' else img_url)
            with io_img:
                org_image = imageio.imread(io_img, as_gray=False, pilmode="RGB")
                # cur_img = cv2.cvtColor(np.asarray(org_image), cv2.COLOR_RGB2GRAY)

            list_letter_image_regions = get_letter_image_regions(org_image)

            cur_result = []
            for letter_bounding_box in list_letter_image_regions:
                x, y, w, h = letter_bounding_box

                # Extract the letter from the original image with a 1-pixel margin around the edge
                cur_img = org_image[y - 1:y + h + 1, x - 1:x + w + 1]
                cur_img = cv2.cvtColor(cur_img, cv2.COLOR_RGB2GRAY)
                cur_img = cv2.resize(cur_img, (30, 30))  # (30, 30)
                cur_img = cv2.threshold(cur_img, 200, 255, cv2.THRESH_BINARY)[1]
                cur_img = np.expand_dims(cur_img, axis=2)  # (30, 30, 1)  # channels
                cur_img = np.expand_dims(cur_img, axis=0)  # (1, 30, 30, 1)
                predict_result = self.model.predict(np.array(cur_img, dtype=float) / 255)
                label = np.argmax(predict_result, axis=1)[0]
                label = '-' if label == 10 else str(label)
                cur_result.append(label)
            return ''.join(cur_result)

        def get_provider_type(t_provider_div: Tag):
            provider_type_text = t_provider_div.text
            _provider_type = re.search("（\\S*）", provider_type_text) if '（' in provider_type_text else \
                re.search("(\\S*)", provider_type_text) if '(' in provider_type_text else None
            if _provider_type is None:
                highlight_print(f'error parser. {provider_type_text:20} not in "(, ("  url:{url}')
                return ''
            _provider_type = _provider_type.group()[:3]
            return _provider_type.replace('（', '')

        def get_detail(_tag_detail: Tag, output_dict: dict) -> None:
            tag_ul_attr = _tag_detail.find('ul', attrs={'class': ["attr", ]})
            result_set_li = tag_ul_attr.findAll('li')
            for tag_li in result_set_li:
                select_item_name = tag_li.text[0: 2]
                if select_item_name not in ('型態', '現況'):
                    continue
                text = tag_li.text
                text = text[text.find(':') + 1:].replace('  ', '')
                dict_attr[select_item_name] = text

        filter_data = SoupStrainer(['div', 'span'],
                                   attrs={'class': ['avatarRight', 'detailInfo clearfix',  # div
                                                    'num']}  # span
                                   )
        parser_data = BeautifulSoup(html_text, 'lxml', parse_only=filter_data)
        if parser_data is None:
            return []

        tag_num_span = parser_data.find('span', attrs={'class': ['num', ]})
        if tag_num_span is None:
            highlight_print(f'error. empty phone number: url: {url} (maybe the page does not exists anymore.)')
            return []
        phone_number = await get_phone_data(tag_num_span)

        # result_set_provider = parser_data.findAll('div', attrs={'class': ['infoOne clearfix'], })
        tag_avatar_right_div = parser_data.find('div', attrs={'class': ['avatarRight'], })
        tag_provider_div = tag_avatar_right_div.find('div')

        provider_name = tag_provider_div.find('i').text
        gender = self.get_gender_by_name(provider_name)

        provider_type = get_provider_type(tag_provider_div)  # 屋主...

        dict_attr = dict(型態='', 現況='')
        tag_detail = parser_data.find('div', attrs={'class': ['detailInfo clearfix'], })
        get_detail(tag_detail, dict_attr)
        house_type, state = dict_attr['型態'], dict_attr['現況']

        return [provider_name, gender, provider_type, house_type, state, phone_number, url]

    def run(self, url_list: list, max_threads: int = 20) -> None:
        loop = asyncio.get_event_loop()
        url_list = self.get_works_url_list(url_list)
        loop.run_until_complete(self._main(url_list, max_threads))

    async def write(self, lists: list, sep='\t') -> bool:
        try:
            self.log(sep.join(lists))
            return True
        except WriteDataFailed as e:
            highlight_print(str(e))
            return False

    @classmethod
    def batch_get_projects_info(cls, input_dict: dict) -> None:
        """

        :param input_dict:  see config.yaml.RentHouse591Info
        :return:
        """

        work_dir, output_file = Path(input_dict['work_dir']), Path(input_dict['output_file'])
        n_cpu, timeout = input_dict.get('n_cpu', cpu_count()), input_dict.get('timeout', 30)
        max_threads: int = input_dict.get('max_threads', 20)
        if n_cpu == -1:
            n_cpu = cpu_count()
        if not work_dir.exists():
            raise FileNotFoundError(str(work_dir.resolve()))

        with open(output_file, 'w') as _f:
            _f.write('\t'.join([title_name for title_name in RentHouse591Info.CSV_TITLE]))

        for cur_url_file in [url_file for url_file in work_dir.glob('*.csv') if url_file.is_file()]:
            csv_file = CSVFile(cur_url_file.resolve(),
                               usecols=range(len(RentHouse591URL.CSV_TITLE)))  # ignore the row data, it columns are not matched with title
            all_url_series = csv_file.df.URL
            max_length = len(all_url_series)
            pool, step = get_pool(n_cpu, work_list_size=max_length)
            t_s = time()
            for spider_url_list in [all_url_series[i: min((i + step), max_length)] for i in range(0, max_length, step)]:
                pool.apply_async(create_spider_and_run, args=(cls, output_file, spider_url_list), kwds={'max_threads': max_threads, 'timeout': timeout})
            pool.close()
            pool.join()
            highlight_print(f'{((time() - t_s) / 60):<8.2f} min')
        startfile(output_file.parent)


def download_image(input_dict: dict):
    import requests

    output_dir: Path = Path(input_dict['output_dir'])
    url_file_path: Path = Path(input_dict['url_file_path'])
    url_column_name = input_dict['url_column_name']
    options = input_dict['options']

    output_ext_name = options.get('ext_name', '')
    if output_ext_name.find('.') == -1:
        output_ext_name = '.' + output_ext_name

    async def download_file(url: URL, out_file: Path, headers=None, **opt):
        chunk_size = opt.get('chunk_size', 4096)  # default 4KB
        max_size = 1024 ** 2 * options.get('max_size', -1)  # MB, default will ignore.
        response = requests.get(url, headers=headers, timeout=opt.get('timeout'))
        if response.status_code != 200:
            raise requests.ConnectionError(f'{response.status_code}')

        with open(str(out_file.resolve()), mode='wb') as out_f:
            cur_size = 0
            for chunk in response.iter_content(chunk_size=chunk_size):
                cur_size += chunk_size
                if 0 < max_size < cur_size:
                    return
                out_f.write(chunk)

    df = pd.read_csv(url_file_path, engine='python', sep=options.get('sep', ','))
    loop = asyncio.get_event_loop()
    list_task = [asyncio.ensure_future(
        download_file('http:' + url if url[0:5] != 'http:' else url, Path(f'{output_dir}/{idx}{output_ext_name}'),
                      headers=options.get('headers'),
                      max_size=options.get('max_size'))
    ) for idx, url in enumerate(df[url_column_name])]
    loop.run_until_complete(asyncio.wait(list_task))


def main(config):
    dict_run = {0: lambda: RentHouse591URL(Path('temp.temp')).start(config['RentHouse591URL']['city_name_list']),
                1: lambda: RentHouse591Info.batch_get_projects_info(config['RentHouse591Info']),
                3: lambda: download_image(config['download_image'])
                }

    func = dict_run.get(config['Action'])
    if func:
        func()


if __name__ == '__main__':
    from yaml import safe_load  # pip install pyyaml

    with open('config.yaml', 'r', encoding='utf-8') as f:
        g_config = safe_load(f)  # reading configuration files is very dangerous because they can allow execution of arbitrary code.
    main(g_config)
