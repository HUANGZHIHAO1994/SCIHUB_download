import requests
import random
from lxml import etree
import re
import json
import pandas as pd
from selenium import webdriver
import time
import os
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
# import pymongo
# from pymongo.errors import DuplicateKeyError

import csv

# MongoDb 配置

# LOCAL_MONGO_HOST = '127.0.0.1'
# LOCAL_MONGO_PORT = 27017
# DB_NAME = 'IPCC'
# #  mongo数据库的Host, collection设置
# client = pymongo.MongoClient(LOCAL_MONGO_HOST, LOCAL_MONGO_PORT)
# collection = client[DB_NAME]["ArticlesPDF"]

PROXY_URL = ""

USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/44.0.2403.155 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2224.3 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36',
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0; Avant Browser; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)',
        'Mozilla/5.0 (X11; Linux i686; rv:64.0) Gecko/20100101 Firefox/64.0',
        'Mozilla/5.0 (X11; Linux i586; rv:63.0) Gecko/20100101 Firefox/63.0',
        'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.10; rv:62.0) Gecko/20100101 Firefox/62.0'
    ]

url = "http://sci-hub.se"


class SCIHUB:

    def __init__(self, start, end):
        self.start = start
        self.end = end

    @staticmethod
    def proxy_ip():
        response = requests.get(PROXY_URL)
        text = response.text
        print('重新获取了一个代理：', text)
        result = json.loads(text)
        if len(result['data']) > 0:
            data = result['data'][0]
            ip = data['ip']
            port = data['port']
            pro_ip = "https://{}:{}".format(ip, port)
            return pro_ip
        else:
            return ''

    def pdf_download(self, url, id, year):
        headers = {}
        headers['User-Agent'] = random.choice(USER_AGENTS)
        ip_proxy1 = {}
        pro_ip = self.proxy_ip()
        if pro_ip != '':
            ip_proxy1["http"] = pro_ip
            r = requests.get(url, stream=True, headers=headers, proxies=ip_proxy1)
        else:
            r = requests.get(url, stream=True, headers=headers)
        # print(r.text)
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'IPCC_PDF')
        if not os.path.exists(path):
            os.mkdir(path)
        if year != '':
            pdfpath = os.path.join(path, year)
            if not os.path.exists(pdfpath):
                os.mkdir(pdfpath)
        else:
            pdfpath = ''
        if pdfpath == '':

            with open(path + "\\" + "{}.pdf".format(id), "wb") as pdf:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        pdf.write(chunk)
        else:
            with open(pdfpath + "\\" + "{}.pdf".format(id), "wb") as pdf:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        pdf.write(chunk)

    def read_result(self):
        df_res = pd.read_csv('./result.csv', sep=',', low_memory=False)
        df_res = df_res.iloc[self.start:self.end, :]
        # print(df_res)
        for i, j in df_res.iterrows():
            id = j["Unnamed: 0"]
            art = j["name1"].strip()
            art = art.replace("\n", ' ')
            print(id)
            print(art)
            if art == '':
                continue
            self.crawl(id, art)


    def crawl(self, id, art):
        chrome_options = Options()
        headers = random.choice(USER_AGENTS)
        # pro_ip = proxy_ip()
        chrome_options.add_argument('--user-agent={}'.format(headers))  # 设置请求头的User-Agent
        # if pro_ip != '':
        #     chrome_options.add_argument("--proxy-server={}".format(pro_ip))  #  设置代理ip
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')  # 不加载图片, 提升速度
        chrome_options.add_argument('--headless')  # 浏览器不提供可视化页面
        # chrome_options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(chrome_options=chrome_options)
        driver.get(url)

        WebDriverWait(driver, 100, 0.5).until(
            EC.presence_of_element_located((By.XPATH, "//div[@id='open']")))
        input = driver.find_element_by_xpath("//input[@name='request']")
        input.send_keys(art)
        time.sleep(0.5)
        open_ = driver.find_element_by_id("open")
        open_.click()
        WebDriverWait(driver, 100, 0.5).until(
            EC.presence_of_element_located((By.XPATH, "//div")))

        print(driver.page_source)
        if ("search temporarily unavailable" in driver.page_source) or ("article not found" in driver.page_source):
            print('*' * 30)
            print("没有这篇文章的pdf:{}".format(art))
            time.sleep(1)
            return
        else:
            self.wri_parse(driver.page_source, id, art)


    def wri_parse(self, source, id, art):
        tree_node = etree.HTML(source)
        #  获取pdf链接：contains ⇣ save
        try:
            href = tree_node.xpath('//div//a[contains(text(),"⇣ save")]/@onclick')[0].replace("location.href=", '').replace(
                "'", '')
            print(href)
        except Exception as e:
            print(e)
            print("没有这篇文章的pdf:{}".format(art))
            return
            # time.sleep(1)
        try:
            authors = tree_node.xpath('//div[@id="citation"]//text()')[0]
            print(authors)
        except:
            authors = ''
        try:
            year = re.findall(r'\(\d+\)', authors)[0].replace('(', '').replace(")", '')
            print(year)
        except:
            year = ''
        try:
            article = tree_node.xpath('//div[@id="citation"]//text()')[1]
            print(article)
        except:
            article = art
        try:
            doi = tree_node.xpath('//div[@id="citation"]//text()')[2].replace("doi:", '').replace("&nbsp;", '').strip()
            print(doi)
        except:
            doi = ''

        pdf_ = []

        pdf_.append(id)
        pdf_.append(article)
        pdf_.append(href)
        pdf_.append(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        pdf_.append(year)
        pdf_.append(authors)
        pdf_.append(doi)

        csv_write.writerow(pdf_)

        try:
            if href:
                self.pdf_download(href, id, year)
        except:
            pass

if __name__ == '__main__':

    out = open('pdf_1.csv', 'a', newline='', encoding='gb18030')
    csv_write = csv.writer(out, dialect='excel')
    # stu1 = ['id', 'title', 'url', 'crawl_time', 'year', 'authors', 'doi']
    # csv_write.writerow(stu1)
    sci = SCIHUB(0, 10)
    sci.read_result()




