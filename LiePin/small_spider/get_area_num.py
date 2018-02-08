from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup as bs
import time
import pymongo

browser = webdriver.Chrome(executable_path='C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe')
wait = WebDriverWait(browser, 10)
client = pymongo.MongoClient(host='120.79.162.44', port=10086)
client.admin.authenticate("Leo", "fwwb123456")
LiePin = client["fwwb"]
LiePin_city = LiePin["LiePin_city"]


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
        if city != None:
            data = {'city': city}
            LiePin_city.insert(data)

if __name__=="__main__":
    search()