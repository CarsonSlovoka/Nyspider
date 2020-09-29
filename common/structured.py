from os import path
import pandas as pd
from pathlib import Path

from typing import NewType, TypeVar, Any
from time import time

from compat import cached_property
from configparser import ConfigParser, ExtendedInterpolation

URL = NewType('URL', str)
T_Path = TypeVar('T_Path', str, Path)
Now = time


class FilePath:
    __slots__ = ['_file_path']

    def __init__(self, file_path: str):
        if not path.exists(file_path):
            raise FileNotFoundError(file_path)
        self._file_path = file_path

    def __repr__(self) -> str:
        return self._file_path

    @property
    def file_path(self) -> str:
        return self._file_path


class CSVFile(FilePath):
    __slots__ = ['_df', ]

    def __init__(self, file_path: T_Path, sep: str = '\t', **option):
        super().__init__(file_path)
        self._df = pd.read_csv(self.file_path, sep=sep, engine=option.get('engine', 'python'), usecols=option.get('usecols'))

    @property
    def df(self) -> pd.DataFrame:
        return self._df


class Website:
    __slots__ = []
    RENT_591 = URL("https://rent.591.com.tw")

    COMMON_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': "1",
        'Connection': 'keep-alive'}


class InIGetter:
    __slots__ = ('_dict_search',)

    def __init__(self, ini_path: Path):
        config = ConfigParser(interpolation=ExtendedInterpolation())  # ConfigParser will see all the variable its type as "str"
        read_config_result = config.read([ini_path, ], encoding='utf-8')
        file_exists = True if len(read_config_result) > 0 else False

        self._dict_search = {}
        for section_name in config.sections():
            for item, value in config.items(section_name):
                self._dict_search[item] = value

    def search_item(self, name: str, default):
        return self._dict_search.get(name, default)

    @property
    def config(self):
        return self.config

    def get(self, name: str, default: Any = None):
        return self.search_item(name, default)


if __name__ == '__main__':
    # below is only for test
    pass
