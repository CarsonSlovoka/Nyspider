import requests


class SpiderBase:
    __slots__ = ('session', 'headers')

    def __init__(self):
        self.session = requests.session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': "1",
            'Connection': 'keep-alive'}

    def run(self):
        raise NotImplementedError

    def spider(self, *args, **kwargs) -> list:
        raise NotImplementedError

    def write(self, list_data: list):
        raise NotImplementedError
