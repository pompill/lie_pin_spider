# -*- coding:utf-8 -*-

# Python内置库
from urllib import parse
import re

# 第三方库
import scrapy
from scrapy.spiders import Spider
# import redis
from lxml import etree
from bs4 import BeautifulSoup as Bs
from LiePin.utils import select_data

# 项目内部库
from LiePin.items import LiePinItem
from LiePin.utils import changeK
from LiePin.utils import changeMs


class LiePinSpider(Spider):
    name = "lie_pin"
    key = parse.quote("大数据")
    start_urls = ['https://www.liepin.com/zhaopin/?pubTime=&ckid=68ec2548afecd7e3&fromSearchBtn=2'
                  '&compkind=&isAnalysis=&init=-1&searchType=1&flushckid=1&dqs={}&industryType=&'
                  'jobKind=&sortFlag=15&industries=&salary=&compscale=&key=' + key +
                  '&clean_condition=&headckid=68ec2548afecd7e3&d_pageSize=40'
                  '&siTag=k_cloHQj_hyIn0SLM9IfRg~fA9rXquZc5IkJpXC-Ycixw&d_headId=04c6a9eba2c03cc4717ec37b59061035'
                  '&d_ckId=04c6a9eba2c03cc4717ec37b59061035&d_sfrom=search_prime&d_curPage=0']
    extra = '&curPage={}'
    # r = redis.Redis(host='localhost', port=6379, db=0)
    http_header = 'https://www.liepin.com'

    def start_requests(self):
            data = select_data.parse()
            for i in data:
                # area = self.r.spop('lie_pin_city_num').decode('utf-8')
                area = i['city']
                yield scrapy.Request(self.start_urls[0].format(area), callback=self.get_info_url, meta={'area': area})

    @staticmethod
    def get_max_page(response):
        try:
            html = response.html
            selector = etree.HTML(html)
            max_page_href = selector.xpath('//div[@class="pagerbar"]/a[@class="last]/@href')
            max_page = re.search('curPage=(\d+)', max_page_href).group(0)
            return max_page
        except Exception as err:
            print(err)
            pass
    def get_info_url(self, response):
        area = response.meta['area']
        html = response.body
        soup = Bs(html, 'html.parser')
        selector = etree.HTML(html)
        if selector.xpath('//div[@class="sojob-result sojob-no-result"]/ul[@class="sojob-list"]'):
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
        elif selector.xpath('//div[@class="sojob-result "]/ul[@class="sojob-list"]'):
            info_url = selector.xpath('//div[@class="job-info"]/h3/a/@href')
            for url in info_url:
                if url[:4] == 'http':
                    yield scrapy.Request(url, callback=self.get_info, meta={'work_info_url': url})
                else:
                    curl = self.http_header + url
                    yield scrapy.Request(curl, callback=self.get_info, meta={'work_info_url': curl})
            if selector.xpath('//div[@class="pagerbar"]/a[@class="last"]/@href'):
                max_page = self.get_max_page(response)
                if max_page != None:
                    for p in range(1, int(max_page)+1):
                        url = self.start_urls[0].format(area) + self.extra.format(p)
                        yield scrapy.Request(url, callback=self.get_formal_url)
                else:
                    pass
        else:
            pass

    def get_formal_url(self, response):
        html = response.body
        selector = etree.HTML(html)
        href = selector.xpath('//div[@class="job-info"]/h3/a/@href')
        for url in href:
            if url[:4] == 'http':
                yield scrapy.Request(url, callback=self.get_info, meta={'work_info_url': url})
            else:
                curl = self.http_header + url
                yield scrapy.Request(curl, callback=self.get_info, meta={'work_info_url': curl})

    @staticmethod
    def get_info(response):
        html = response.body
        selector = etree.HTML(html)
        item = LiePinItem()
        salary = selector.xpath('//div[@class="job-title-left"]/p/text()')[0].replace('万', '').split('-')
        location = selector.xpath('string(//p[@class="basic-infor"]/span[1])').strip()
        business_name = selector.xpath('string(//div[@class="title-info"]/h3/a)')
        business_location = selector.xpath('string(//ul[@class="new-compintro"]/li[3])')[5:]
        business_info = selector.xpath('string(//div[@class="info-word"])').strip()
        command = selector.xpath('string(//div[@class="content content-word"])').strip()
        if len(salary) == 2:
            min_salary = changeK.change_to_k(int(salary[0])*10000)
            max_salary = changeK.change_to_k(int(salary[1])*10000)
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
        if selector.xpath('//div[@class="content"]/ul/li[1]/label'):
            career_type = selector.xpath('string(//div[@class="content"]/ul/li[1]/label)')
        elif selector.xpath('//div[@class="content content-word"]'):
            try:
                career_type = selector.xpath('//div[@class="content content-word"]/ul/li[1]/@title')[0]
            except Exception as err:
                print(err)
                career_type = '无'
        else:
            career_type = '无'
        if selector.xpath('//ul[@class="new-compintro"]'):
            business_count = selector.xpath('string(//ul[@class="new-compintro"]/li[2])')[5:]
        elif selector.xpath('//div[@class="content content-word"]'):
            business_count = selector.xpath('string(//div[@class="content content-word"]/li[6])').replace('企业规模：', '')
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
        item['work_info_url'] = response.meta['work_info_url']
        yield item
