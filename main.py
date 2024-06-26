from selenium import webdriver
from selenium_stealth import stealth
import undetected_chromedriver as uc
from logging import config
from eupay import EUPay
import pickle
import pandas

from src.spp.types import SPP_document

config.fileConfig('dev.logger.conf')


def driver():
    """
    Selenium web driver
    """
    options = webdriver.ChromeOptions()

    # Параметр для того, чтобы браузер не открывался.
    # options.add_argument('headless')

    options.add_argument('start-maximized')
    options.add_argument('window-size=1920x1080')
    options.add_argument("disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    _driver = webdriver.Chrome(options)

    stealth(_driver,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36',
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            run_on_insecure_origins=False,
            )

    return _driver


def driver2():
    __driver = uc.Chrome(headless=False, use_subprocess=True)
    return __driver


def to_dict(doc: SPP_document) -> dict:
    return {
        'title': doc.title,
        'abstract': doc.abstract,
        'text': doc.text,
        'web_link': doc.web_link,
        'local_link': doc.local_link,
        'other_data': doc.other_data.get('category') if doc.other_data.get('category') else '',
        'pub_date': str(doc.pub_date.timestamp()) if doc.pub_date else '',
        'load_date': str(doc.load_date.timestamp()) if doc.load_date else '',
    }


if __name__ == '__main__':
    parser = EUPay(driver2(), max_count_documents=5)
    docs: list[SPP_document] = parser.content()

    print(*docs, sep='\n\r\n')
    print(len(docs))
