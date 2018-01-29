from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup as bs
import time
import redis

browser = webdriver.Chrome(executable_path='C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe')
wait = WebDriverWait(browser, 10)
r = redis.Redis(host='localhost',port=6379,db=0)
def search():
    try:
        browser.get('https://www.liepin.com/zhaopin/?d_sfrom=search_fp_nvbar&init=1')
        button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'li[class="city-select"]')))
        button.click()
        time.sleep(1)
        # browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        click_province()
    except TimeoutException:
        search()

def click_province():
    for i in range(1,28):
        province_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@class="data-list"]/ul/li[{}]/a'.format(i))))
        province_button.click()
        get_area_num()
        country_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@class="data-tabs"]/ul/li[1]')))
        country_button.click()

def get_area_num():
    html = browser.page_source
    soup = bs(html,'html.parser')
    city_total = soup.select('ul[class="clearfix"] li a')
    for n in city_total:
        city = n.get('data-code')
        r.sadd('lie_pin_city_num',city)
if __name__=="__main__":
    search()