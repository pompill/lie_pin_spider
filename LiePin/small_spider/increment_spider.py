# -*- coding:utf-8 -*-

# Python内置库
from urllib import parse
import re
import schedule

# 第三方库
import scrapy
from lxml import etree
from bs4 import BeautifulSoup as Bs
from LiePin.utils import select_data
import hashlib
import pymongo
import requests

# 项目内部库
from LiePin.utils import changeK
from LiePin.utils import changeMs


class IncrementSpider(object):
    def __init__(self):
        self.name = "lie_pin"
        self.key = parse.quote("大数据")
        self.start_urls = ['https://www.liepin.com/zhaopin/?pubTime=&ckid=68ec2548afecd7e3&fromSearchBtn=2'
                      '&compkind=&isAnalysis=&init=-1&searchType=1&flushckid=1&dqs={}&industryType=&'
                      'jobKind=&sortFlag=15&industries=&salary=&compscale=&key=' + self.key +
                      '&clean_condition=&headckid=68ec2548afecd7e3&d_pageSize=40'
                      '&siTag=k_cloHQj_hyIn0SLM9IfRg~fA9rXquZc5IkJpXC-Ycixw&d_headId=04c6a9eba2c03cc4717ec37b59061035'
                      '&d_ckId=04c6a9eba2c03cc4717ec37b59061035&d_sfrom=search_prime&d_curPage=0']
        self.extra = '&curPage={}'
        self.http_header = 'https://www.liepin.com'
        self.header = {'user-agent': 'Mozilla/5.0 (Windows NT 6.3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36',}
        self.client = pymongo.MongoClient(host='120.79.162.44', port=10086)
        self.client.admin.authenticate('Leo', 'fwwb123456')
        self.LiePin = self.client['fwwb']
        self.LiePinData = self.LiePin['LiePinData']

    def req(self, url):
        response = requests.get(url=url, headers=self.header)
        return response

    @staticmethod
    def html(response):
        html = response.content.decode('utf-8')
        return html

    def get_max_page(self, response):
        try:
            selector = etree.HTML(self.html(response))
            max_page_href = selector.xpath('//div[@class="pagerbar"]/a[@class="last"]/@href')[0]
            max_page = re.findall('&curPage=(\d+)', max_page_href)[0]
            return max_page
        except Exception as err:
            print(err)
            pass

    def insufficient(self, response):
        selector = etree.HTML(self.html(response))
        icon = selector.xpath('//div[@class="sojob-result sojob-no-result"]/ul[@class="sojob-list"]')
        return icon

    def insufficient_info_url(self, response):
        soup = Bs(self.html(response), 'html.parser')
        selector = etree.HTML(self.html(response))
        for i, v in enumerate(soup.select('.job-content div ul li')):
            if re.findall('<li class="downgrade-search"', str(v)):
                if i != 0:
                    info_url = selector.xpath('//div[@class="job-info"]/h3/a/@href')[:i]
                    for url in info_url:
                        if url[:4] == 'http':
                            yield scrapy.Request(url, callback=self.get_info, meta={'work_info_url': url})
                        else:
                            curl = self.http_header + url
                            yield scrapy.Request(curl, callback=self.get_info, meta={'work_info_url': curl})

    def get_info_url(self, response):
        selector = etree.HTML(self.html(response))
        info_url = selector.xpath('//div[@class="job-info"]/h3/a/@href')
        for i_url in info_url:
            if i_url[:4] == 'http':
                info_url_res = self.req(url=i_url)
                self.get_info(info_url_res)
            else:
                curl = self.http_header + i_url
                info_url_res = self.req(url=curl)
                self.get_info(info_url_res)

    def next_page_icon(self, response):
        selector = etree.HTML(self.html(response))
        next_page_href = selector.xpath('//div[@class="pagerbar"]/a[@class="last"]/@href')
        return next_page_href

    def get_info(self, response):
        selector = etree.HTML(self.html(response))
        item = {}
        try:
            salary = selector.xpath('//div[@class="job-title-left"]/p/text()')[0].replace('万', '').split('-')
            location = selector.xpath('string(//p[@class="basic-infor"]/span[1])').strip()
            business_name = selector.xpath('string(//div[@class="title-info"]/h3/a)')
            business_location = selector.xpath('string(//ul[@class="new-compintro"]/li[3])')[5:]
            business_info = selector.xpath('string(//div[@class="info-word"])').strip()
            command = selector.xpath('string(//div[@class="content content-word"])').strip()
            if len(salary) == 2:
                min_salary = changeK.change_to_k(int(salary[0]) * 10000)
                max_salary = changeK.change_to_k(int(salary[1]) * 10000)
            else:
                min_salary = re.sub('\s+', '', salary[0]).strip()
                max_salary = re.sub('\s+', '', salary[0]).strip()
            h = re.sub('\r\n\s+', '', str(command))
            if re.findall('岗位职责(.*?)任职资格', str(h)):
                try:
                    work_duty = re.findall('岗位职责(.*?)任职资格', str(h))[0].replace(':', '').replace('：', '')
                    work_need = re.findall('任职资格(.*?)。', str(h))[0].replace(':', '').replace('：', '')
                    work_duty_content = ''
                except Exception as err:
                    print(err)
                    work_duty = ''
                    work_need = ''
                    work_duty_content = h[0:500]
            elif re.findall('岗位职责(.*?)任职资格(.*?)岗位说明', str(h)):
                try:
                    work_duty = re.findall('岗位职责(.*?)任职资格', str(h))[0].replace(':', '').replace('：', '')
                    work_need = re.findall('任职资格(.*?)岗位说明', str(h))[0].replace(':', '').replace('：', '')
                    work_duty_content = ''
                except Exception as err:
                    print(err)
                    work_duty = ''
                    work_need = ''
                    work_duty_content = h[0:500]
            else:
                work_duty = ''
                work_need = ''
                work_duty_content = h[0:500]
                pass
            if selector.xpath('//div[@class="job-qualifications"]'):
                limit_degree = selector.xpath('string(//div[@class="job-qualifications"]/span[1])')
                work_experience = selector.xpath('string(//div[@class="job-qualifications"]/span[2])')
            elif selector.xpath('//div[@class="resume clearfix"]'):
                limit_degree = selector.xpath('string(//div[@class="resume clearfix"]/span[1])')
                work_experience = selector.xpath('string(//div[@class="resume clearfix"]/span[2])')
            else:
                limit_degree = '无'
                work_experience = '无'
            if selector.xpath('//div[@class="title-info"]/h1'):
                career_type = selector.xpath('string(//div[@class="title-info"]/h1)').replace('\d+', '')
            else:
                career_type = ''
            if selector.xpath('//ul[@class="new-compintro"]'):
                business_count = selector.xpath('string(//ul[@class="new-compintro"]/li[2])')[5:]
            elif selector.xpath('//div[@class="content content-word"]'):
                business_count = selector.xpath(
                    'string(//div[@class="content content-word"]/li[6])').replace('企业规模：', '')
            else:
                business_count = '无'
            if selector.xpath('//ul[@class="new-compintro"]/li[1]/a'):
                business_type = selector.xpath('string(//ul[@class="new-compintro"]/li[1]/a)')
            elif selector.xpath('//ul[@class="new-compintro"]/li[1]'):
                business_type = selector.xpath('string(//ul[@class="new-compintro"]/li[1])')
            else:
                business_type = '无'
            if selector.xpath('string(//div[@class="content"]/ul/li[1]/label)') != '':
                business_industry = selector.xpath('string(//div[@class="content"]/ul/li[1]/label)')
            else:
                business_industry = '无'
            if selector.xpath('//p[@class="basic-infor"]/time/@title'):
                date = selector.xpath('//p[@class="basic-infor"]'
                                      '/time/@title')[0].replace(
                    '年', '-').replace(
                    '月', '-').replace(
                    '日', '')
            elif selector.xpath('//p[@class="basic-infor"]/span[2]'):
                date = selector.xpath('string(//p[@class="basic-infor"]/span[2])')
            else:
                date = ''
            try:
                business_website = selector.xpath('//div[@class="title-info"]/h3/a/@href')[0]
            except Exception as err:
                print(err)
                business_website = ''
                pass
            publish_date = changeMs.change_ms(date)
            string = career_type + business_name
            item['_id'] = hashlib.md5(string.encode('utf-8')).hexdigest()
            item['from_website'] = '猎聘'
            item['min_salary'] = min_salary
            item['max_salary'] = max_salary
            item['location'] = location
            item['publish_date'] = publish_date
            item['limit_degree'] = limit_degree
            item['work_experience'] = work_experience
            item['people_count'] = 0
            item['career_type'] = career_type
            item['business_name'] = business_name
            item['business_website'] = business_website
            item['business_type'] = business_type
            item['business_location'] = business_location
            item['business_count'] = business_count
            item['business_industry'] = business_industry
            item['business_info'] = business_info
            item['work_type'] = '全职'
            item['work_duty'] = work_duty
            item['work_need'] = work_need
            item['work_duty_content'] = work_duty_content
            item['work_info_url'] = response.url
            self.LiePinData.insert(item)
        except Exception as err:
            print(err)

    def do(self):
        data = select_data.parse()
        for i in data:
            area = i['city']
            response = self.req(url=self.start_urls[0].format(area))
            if self.insufficient(response):
                self.insufficient_info_url(response=response)
            else:
                self.get_info_url(response=response)
                if self.next_page_icon(response=response):
                    max_page = self.get_max_page(response)
                    print(max_page)
                    if max_page != '':
                        for p in range(1, int(max_page) + 1):
                            next_url = self.start_urls[0].format(area) + self.extra.format(p)
                            next_page_res = self.req(url=next_url)
                            self.get_info_url(response=next_page_res)
                    else:
                        pass

    def main(self):
        work = self.do()
        schedule.every(1).days.do(work)

increment_spider = IncrementSpider().main()


