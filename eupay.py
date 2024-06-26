"""
Нагрузка плагина SPP

1/2 документ плагина
"""
import logging
import time
import dateparser
from datetime import datetime, date

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from src.spp.types import SPP_document
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class EUPay:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'eupay'
    _content_document: list[SPP_document]
    HOST = 'https://www.europeanpaymentscouncil.eu/search'

    def __init__(self, webdriver: WebDriver, last_document: SPP_document = None,
                 max_count_documents: int = 100):
        """
        Конструктор класса парсера

        По умолчанию внего ничего не передается, но если требуется (например: driver селениума), то нужно будет
        заполнить конфигурацию
        """
        # Обнуление списка
        self._content_document = []

        self.driver = webdriver

        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            'source': '''
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                  '''
        })

        self.wait = WebDriverWait(self.driver, timeout=20)
        self.max_count_documents = max_count_documents
        self.last_document = last_document

        # Логер должен подключаться так. Вся настройка лежит на платформе
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Parser class init completed")
        self.logger.info(f"Set source: {self.SOURCE_NAME}")
        ...

    def content(self) -> list[SPP_document]:
        """
        Главный метод парсера. Его будет вызывать платформа. Он вызывает метод _parse и возвращает список документов
        :return:
        :rtype:
        """
        self.logger.debug("Parse process start")
        try:
            self._parse()
        except Exception as e:
            self.logger.debug(f'Parsing stopped with error: {e}')
        else:
            self.logger.debug("Parse process finished")
        return self._content_document

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        for page_url in self._encounter_pages():
            for doc in self._collect_docs(page_url):
                self._initial_access_source(doc.web_link, 3)
                if len(self.driver.find_elements(By.CLASS_NAME, 'content-container-details')) > 0:
                    try:
                        doc_text = self.driver.find_element(By.CLASS_NAME, 'content-container-details').find_element(
                            By.TAG_NAME, 'p').text
                    except:
                        doc_text = self.driver.find_element(By.CLASS_NAME, 'content-container-details').text
                elif len(self.driver.find_elements(By.CLASS_NAME, 'col-md-6')) > 0:
                    doc_text = self.driver.find_element(By.CLASS_NAME, 'col-md-6').text
                else:
                    doc_text = self.driver.find_element(By.TAG_NAME, 'article').find_element(By.CLASS_NAME,
                                                                                             'content').text
                doc.text = doc_text
                doc.load_date = datetime.now()
                doc.abstract = None

                self.find_document(doc)

    def _encounter_pages(self) -> str:
        _base = self.HOST
        _params = '?page='
        page = 0
        while True:
            url = _base + _params + str(page)
            page += 1
            yield url

    def _initial_access_source(self, url: str, delay: int = 2):
        self.driver.get(url)
        self.logger.debug('Entered on web page ' + url)
        time.sleep(delay)
        self._agree_cookie_pass()

    def _collect_docs(self, url: str) -> list[SPP_document]:
        try:
            self._initial_access_source(url)
            self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'view-content')))
        except Exception as e:
            raise NoSuchElementException() from e

        links = []
        try:
            articles = self.driver.find_elements(By.TAG_NAME, 'article')
        except Exception as e:
            raise NoSuchElementException('list is empty') from e
        else:
            for i, el in enumerate(articles):
                web_link = None
                try:
                    try:
                        _title = el.find_element(By.CLASS_NAME, 'kb-title')
                        title_text = _title.text
                    except:
                        _title = el.find_element(By.CLASS_NAME, 'well').find_element(By.TAG_NAME, 'h2')
                        title_text = _title.text

                    web_link = _title.find_element(By.TAG_NAME, 'a').get_attribute('href')

                    try:
                        if len(el.find_elements(By.CLASS_NAME, 'kb-type')) > 0:
                            doc_type = el.find_element(By.CLASS_NAME, 'kb-type').text
                        elif len(el.find_elements(By.CLASS_NAME, 'news-type')) > 0:
                            doc_type = el.find_element(By.CLASS_NAME, 'news-type').text
                        elif len(el.find_elements(By.CLASS_NAME, 'label-alt')) > 0:
                            doc_type = el.find_element(By.CLASS_NAME, 'label-alt').text
                        else:
                            doc_type = None
                    except:
                        doc_type = None
                    try:
                        if len(el.find_elements(By.CLASS_NAME, 'kb-intro')) > 0:
                            date_text = el.find_element(By.CLASS_NAME, 'kb-intro').find_element(By.CLASS_NAME,
                                                                                                     'date').text
                        elif len(el.find_elements(By.CLASS_NAME, 'field--created')) > 0:
                            date_text = el.find_element(By.CLASS_NAME, 'field--created').text
                        else:
                            date_text = datetime.strftime(date(2000, 1, 1), format='%Y-%m-%d')
                        parsed_date = dateparser.parse(date_text)
                    except:
                        continue

                    try:
                        tags = el.find_element(By.CLASS_NAME, 'kb-tags').text
                    except:
                        tags = None

                except Exception as e:
                    self.logger.debug(NoSuchElementException(
                        'Страница не открывается или ошибка получения обязательных полей. URL: '+str(web_link)))
                    continue
                else:
                    _doc = SPP_document(None, title_text, None, None, web_link, None, {
                        'doc_type': doc_type,
                        'tags': tags,
                    }, parsed_date, None)
                    links.append(_doc)
        return links

    def _agree_cookie_pass(self):
        """
        Метод прожимает кнопку agree на модальном окне
        """
        cookie_agree_xpath = '//button[text() = \'Accept All Cookies\']'

        try:
            cookie_button = self.driver.find_element(By.XPATH, cookie_agree_xpath)
            if WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(cookie_button)):
                cookie_button.click()
                self.logger.debug(F"Parser pass cookie modal on page: {self.driver.current_url}")
        except NoSuchElementException as e:
            self.logger.debug(f'modal agree not found on page: {self.driver.current_url}')

    @staticmethod
    def _find_document_text_for_logger(self, doc: SPP_document):
        """
        Единый для всех парсеров метод, который подготовит на основе SPP_document строку для логера
        :param doc: Документ, полученный парсером во время своей работы
        :type doc:
        :return: Строка для логера на основе документа
        :rtype:
        """
        return f"Find document | name: {doc.title} | link to web: {doc.web_link} | publication date: {doc.pub_date}"

    def find_document(self, doc: SPP_document):
        """
        Метод для обработки найденного документа источника
        """
        if self.last_document and self.last_document.hash == doc.hash:
            raise Exception(f"Find already existing document ({self.last_document})")

        self._content_document.append(doc)
        self.logger.info(self._find_document_text_for_logger(self, doc))

        if self.max_count_documents and len(self._content_document) >= self.max_count_documents:
            raise Exception(f"Max count articles reached ({self.max_count_documents})")
