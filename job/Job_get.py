# coding:utf-8
from bs4 import BeautifulSoup, SoupStrainer
import requests
import time

import abc
import typing
import traceback

# from Carson3.Class.Logging import CLogging
from Logging import CLogging


class _SpiderBase(abc.ABC):
    def __init__(self, log_name):
        __slot__ = ['session', 'log', 'headers', '_work_list']
        self.session = requests.session()
        # self.log = open(f'{log_name}.txt', 'w', encoding='utf-8')  # If you use this method and you do not use "with" or "close" (guarantee that "close" will be executed) that will lose all the data when the program crashes.
        self._log = CLogging("logger_name", f'{log_name}.txt')
        self.log = self._log.info
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:39.0) Gecko/20100101 Firefox/39.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': "1",
            'Connection': 'keep-alive'}
        self._work_list = []

    @property
    def work_list(self):
        return self._work_list

    def set_work_list(self, data_list: typing.List[typing.Tuple]):
        """

        :param data_list: [(query_url,  total_page), (query_url2,  total_page2) ...]
        :return:
        """

        self._work_list = data_list

    def run(self):
        for query_url, total_page in self.work_list:
            for cur_page in range(total_page):
                try:
                    lists = self.spider(cur_page, query_url)
                    self.write(lists)
                except Exception as e:
                    print(traceback.format_exc())
                    print(str(e))
        self._log.close()

    @abc.abstractmethod
    def spider(self, page, name) -> list:
        return []

    @abc.abstractmethod
    def write(self, list_data: list):
        pass


class Ganji(_SpiderBase):
    def __init__(self, log_name='Ganji'):
        _SpiderBase.__init__(self, log_name)

    def write(self, lists):
        for i in lists:
            self.log.write(i.find('dt').find('a').get_text() + ' ')
            self.log.write(i.find('dd', attrs={'class': 'company'}).find('a').get('title') + ' ')
            self.log.write(i.find('dd', attrs={'class': 'pay'}).get_text() + '\n\n')

    def spider(self, page, name):
        lists = []
        html = requests.get('http://dg.ganji.com/zpwaimaozhuanyuan/' + name + '/o' + str(page + 1) + '/', headers=self.headers).text
        soup = BeautifulSoup(html, "lxml")
        table = soup.find('div', attrs={'id': 'list-job-id'})
        if table:
            lists = table.find_all('dl', attrs={'class': 'list-noimg job-list clearfix'})
        return lists


class Job_58(_SpiderBase):
    def __init__(self, log_name='Job_58'):
        super().__init__(log_name)
        self.f = open('job_58.txt', 'w')

    def write(self, lists):
        for i in lists:
            self.f.write(i.find('dt').find('a').get_text().replace('\n', ' '))
            self.f.write(i.find('dd', attrs={'class': 'w271'}).get_text().replace('\n', ' '))
            self.f.write(i.find('dd', attrs={'class': 'w96'}).get_text() + '\n\n')

    def spider(self, page, name):
        lists = []
        html = requests.get('http://dg.58.com/' + name + '/zpshangwumaoyi/pn' + str(page + 1) + '/', headers=self.headers).text
        soup = BeautifulSoup(html, "lxml")
        table = soup.find('div', attrs={'id': 'infolist'})
        if table is not None:
            lists = table.find_all('dl')
        return lists


class Job_5156(_SpiderBase):
    def __init__(self, log_name='Job_5156'):
        super(Job_5156, self).__init__(log_name)

    def write(self, lists):
        for i in lists:
            self.log.write(i.find('div', attrs={'class': 't1'}).find('a').get('title') + ' ')
            self.log.write(i.find('div', attrs={'class': 't2'}).find('a', attrs={'class': 'comName'}).get('title') + ' ')
            self.log.write(i.find('div', attrs={'class': 't2'}).find('span').get_text().replace('\n', ' ').lstrip() + '\n\n')

    def spider(self, page, query_url):
        lists = []
        html = self.session.get(f'{query_url}+pn={page}', headers=self.headers).text
        soup = BeautifulSoup(html, "lxml")
        table = soup.find('div', attrs={'id': 'js_jobSearch'})
        if table:
            lists = table.find_all('div', attrs={'class': 'postItem'})
        return lists


class Job_cn(_SpiderBase):
    def __init__(self, log_name='job_cn'):
        super(Job_cn, self).__init__(log_name)

    def write(self, lists):
        for i in lists:
            self.log.write(i.find('h4', attrs={'class': 'job_name'}).get_text().replace('\n', ' '))
            self.log.write(i.find('div', attrs={'class': 'job_info'}).find('a').get('title').replace('\n', ' ') + '   ')

            find_result = i.find('a', attrs={'class': 'job_check '})
            if find_result:
                get_id = find_result.get('data-value')
                html = requests.get('http://www.jobcn.com/search/position_detail.uhtml?ids=' + get_id, headers=self.headers).text
                soup = BeautifulSoup(html, "lxml")
                self.log.write(soup.find('div', attrs={'class': 'gl_wk'}).get_text().replace('工作地址：', '') + '\n\n')

    def spider(self, page, name):
        if name is None:
            name = 'http://www.jobcn.com/search/result.xhtml?s=search%2Findex&p.sortBy=default&p.jobLocationId=3002&p.jobLocationTown=%C6%F3%CA%AF%D5%F2%3B%C7%C5%CD%B7%D5%F2%3B%D5%C1%C4%BE%CD%B7%D5%F2%3B%B4%F3%C1%EB%C9%BD%D5%F2%3B%C7%E5%CF%AA%D5%F2%3B%CC%C1%CF%C3%D5%F2%3B%BB%A2%C3%C5%D5%F2%3B%B7%EF%B8%DA%D5%F2%3B%B3%A4%B0%B2%D5%F2%3B%B3%A3%C6%BD%D5%F2&p.jobLocationTownId=300209%2C300211%2C300215%2C300216%2C300220%2C300223%2C300224%2C300226%2C300227%2C300230&p.keyword=%CD%E2%C3%B3&p.keywordType=2#P'
        lists = []
        html = requests.get(f'{name}{page + 1}', headers=self.headers).text
        soup = BeautifulSoup(html, "lxml")
        table = soup.find('form', attrs={'id': 'result_data'})
        if table:
            lists = table.find_all('div', attrs={'class': 'item_box'})
        return lists


class Job_51(_SpiderBase):
    def __init__(self, log_name='job_51'):
        super(Job_51, self).__init__(log_name)

    def write(self, lists):
        for i in lists:
            self.log.write(i.find('td', attrs={'class': 'td1'}).find('a').get_text().replace('\n', ' ') + '  ')
            self.log.write(i.find('td', attrs={'class': 'td2'}).find('a').get_text().replace('\n', ' ') + '  ')
            self.log.write(i.find('td', attrs={'class': 'td3'}).get_text() + '\n\n')

    def spider(self, page, name):
        lists = []
        html = requests.get(
            f'http://search.51job.com/list/030800,0308{name},0000,00,9,99,%25CD%25E2%25C3%25B3,1,1.html?lang=c&stype=1&postchannel=0000&workyear=99&cotype=99&degreefrom=99&jobterm=01&companysize=99&lonlat=0%2C0&radius=-1&ord_field=0&list_type=0&confirmdate=9&fromType=17',
            headers=self.headers).text.encode('ISO-8859-1').decode('gb2312', 'ignore')
        soup = BeautifulSoup(html, "lxml")
        table = soup.find('table', attrs={'id': 'resultList'})
        if table:
            lists = table.find_all('tr', attrs={'class': 'tr0'})
        return lists


class TAAA(_SpiderBase):  # TAIPEI ASSOCIATION OF ADVERTISING AGENCIES
    """
        function crate date: 2019/09/03
    """
    def __init__(self, log_name='TAAA'):
        super().__init__(log_name)

    def write(self, lists):
        if len(lists) > 0:
            self.log('\t'.join(lists))  # output extension: csv, sep="\t"

    def spider(self, page, name) -> list:
        lists = []
        url = f'http://www.taaa.org.tw/company/{page}'
        server_response = requests.get(url, headers=self.headers)
        if server_response.status_code != 200:
            print(f'error to connect:{url}')
            return []

        filter_data = SoupStrainer('div', attrs={'class': ['sider-info']})
        parsed_slide_info = BeautifulSoup(server_response.text, 'lxml', parse_only=filter_data)
        if parsed_slide_info is None:
            return []

        contact_info = parsed_slide_info.find('div', attrs={'class': ['info']})
        # contact_info.find('p', string=self.query_list[idx]).find_next_siblings()
        if contact_info is None:
            print(f'parse error. msg: no slide info. url: {url}')
            return []

        p_datas = contact_info.findAll('p')  # contact_info.find('p').find_next_siblings()
        dict_record = dict(add="", tel="", fax="", email="", site="")
        for p in p_datas:
            key_name = p.attrs['class'][0]
            if key_name in dict_record:
                text = p.text
                for ignore_text in ('電話：', '傳真：', 'E-mail：', '網站：'):
                    if text.find(ignore_text) != -1:
                        text = text.replace(ignore_text, "")
                        break  # There can be only one
                dict_record[key_name] = text
        contact_info_list = [e for e in dict_record.values()]

        filter_data = SoupStrainer('h3', attrs={'class': ['page-title']})
        parsed_company_name = BeautifulSoup(server_response.text, 'lxml', parse_only=filter_data)
        company_name = parsed_company_name.text if parsed_company_name else ""
        lists = [url, company_name]
        lists.extend(contact_info_list)
        return lists


class Job_get():
    def __init__(self):
        self.ganji_work_list = [('changan', 2), ('dalingshan', 1), ('humen', 2)]

        self.job_51_work_list = [('09', 1), ('11', 1), ('20', 1), ('21', 1), ]

        self.job_58_work_list = [('changanqv', 1), ('dalingshan', 1), ('changpingshi', 1), ]

        tmp_url = 'http://s.job5156.com/s/p/result?keywordType=0&keyword=%E5%A4%96%E8%B4%B8&locationList='
        self.job_5156_work_list = [(f'{tmp_url}14010500%2C14010600%2C14011000&posTypeList=&industryList=&updateIn=90&salary=&salaryUnPublic=1&gender=&age=&', 0),
                                   (
                                   f'{tmp_url}14011100%2C14012000%2C14012100&posTypeList=&industryList=&updateIn=90&degreeFrom=1&degreeTo=8&degreeUnlimit=1&workyearFrom=-1&workyearTo=11&workyearUnlimit=1&salary=&salaryUnPublic=1&propertyList=1&gender=&age=&',
                                   1),
                                   (
                                   f'{tmp_url}14012400%2C14012700%2C14012800&posTypeList=&industryList=&updateIn=90&degreeFrom=1&degreeTo=8&degreeUnlimit=1&workyearFrom=-1&workyearTo=11&workyearUnlimit=1&salary=&salaryUnPublic=1&propertyList=1&gender=&age=&',
                                   2),
                                   ]
        self.job_cn_work_list = [(None, 1,), (None, 2)]

        self.taaa_work_list = [(None, 194)]

    def run(self):
        for point_object, work_list in [(TAAA, self.taaa_work_list),
                                        # (Ganji, self.ganji_work_list),
                                        # (Job_51, self.job_51_work_list),
                                        # (Job_58, self.job_58_work_list),
                                        # (Job_5156, self.job_5156_work_list),
                                        # (Job_cn, self.job_cn_work_list),
                                        ]:
            obj = point_object()
            obj.set_work_list(work_list)
            obj.run()
            print(f'{point_object.__name__} OK')


if __name__ == '__main__':
    while True:
        work = Job_get()
        work.run()
        print("sleep...")
        time.sleep(600)
