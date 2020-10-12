from typing import List
import logging
from pathlib import Path


class LogMixin:
    __slots__ = ()

    SEP = '\t'
    _log: logging.Logger

    @staticmethod
    def new_logger(logger_name: str, output_path: Path, **options):
        log = logging.Logger(logger_name)
        file_handler = logging.FileHandler(output_path, mode=options.get('mode', 'w'), encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(u'%(message)s'))
        log.addHandler(file_handler)
        return log

    def log(self, msg_list: List[str]):
        self._log.info(self.SEP.join(msg_list))
