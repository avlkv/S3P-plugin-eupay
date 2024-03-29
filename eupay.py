"""
Нагрузка плагина SPP

1/2 документ плагина
"""
import logging
import time
import dateparser
from datetime import datetime, date
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from src.spp.types import SPP_document
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class EUPAY:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'eupay'
    _content_document: list[SPP_document]
    HOST = 'https://www.europeanpaymentscouncil.eu/search'

    def __init__(self, webdriver: WebDriver, source_type: str, last_document: SPP_document = None,
                 max_count_documents: int = 100,
                 *args, **kwargs):
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
        if source_type:
            self.SOURCE_TYPE = source_type
        else:
            raise ValueError('source_type must be a type of source: "FILE" or "NATIVE"')

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

        for page in self._encounter_pages():
            self.driver.get(page)
            time.sleep(1)

            try:
                all_cookies_btn = self.driver.find_element(By.XPATH, '//button[text() = \'Accept All Cookies\']')
                all_cookies_btn.click()
            except:
                pass

            doc_rows = self.driver.find_elements(By.CLASS_NAME, 'views-row')
            for doc_row in doc_rows:

                try:
                    title = doc_row.find_element(By.CLASS_NAME, 'kb-title')
                except:
                    title = doc_row.find_element(By.CLASS_NAME, 'well').find_element(By.TAG_NAME, 'h2')
                finally:
                    title_text = title.text

                web_link = title.find_element(By.TAG_NAME, 'a').get_attribute('href')

                if len(doc_row.find_elements(By.CLASS_NAME, 'kb-type')) > 0:
                    doc_type = doc_row.find_element(By.CLASS_NAME, 'kb-type').text
                elif len(doc_row.find_elements(By.CLASS_NAME, 'news-type')) > 0:
                    doc_type = doc_row.find_element(By.CLASS_NAME, 'news-type').text
                elif len(doc_row.find_elements(By.CLASS_NAME, 'label-alt')) > 0:
                    doc_type = doc_row.find_element(By.CLASS_NAME, 'label-alt').text
                else:
                    doc_type = ''

                if len(doc_row.find_elements(By.CLASS_NAME, 'kb-intro')) > 0:
                    date_text = doc_row.find_element(By.CLASS_NAME, 'kb-intro').find_element(By.CLASS_NAME, 'date').text
                elif len(doc_row.find_elements(By.CLASS_NAME, 'field--created')) > 0:
                    date_text = doc_row.find_element(By.CLASS_NAME, 'field--created').text
                else:
                    date_text = datetime.strftime(date(2000, 1, 1), format='%Y-%m-%d')

                parsed_date = dateparser.parse(date_text)
                date_str = datetime.strftime(parsed_date, format='%Y-%m-%d %H:%M:%S')

                try:
                    tags = doc_row.find_element(By.CLASS_NAME, 'kb-tags').text
                except:
                    tags = ''

                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.driver.get(web_link)

                try:
                    all_cookies_btn = self.driver.find_element(By.XPATH, '//button[text() = \'Accept All Cookies\']')
                    all_cookies_btn.click()
                except:
                    pass

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

                other_data = {'doc_type': doc_type,
                              'tags': tags}

                abstract = None

                doc = SPP_document(None,
                                   title_text,
                                   abstract,
                                   doc_text,
                                   web_link,
                                   None,
                                   other_data,
                                   parsed_date,
                                   datetime.now())

                self.find_document(doc)

                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

            try:
                next_page = self.driver.find_element(By.XPATH, '//li[@class=\'next\']').find_element(By.TAG_NAME, 'a')
                next_page.click()
                self.logger.debug('Выполнен переход на новую страницу')
                time.sleep(5)
            except:
                self.logger.debug('Не найдено переходов на след. страницу')
                break

        # ---
        # ========================================
        ...

    def _encounter_pages(self) -> str:
        _base = self.HOST
        _params = '?page='
        page = 0
        while True:
            url = _base + _params + str(page)
            page += 1
            yield url

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
