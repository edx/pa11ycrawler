# pylint: disable=missing-docstring
from unittest import TestCase

from freezegun import freeze_time
from scrapy.utils.test import get_crawler

from pa11ycrawler.spiders.pa11y_spider import Pa11ySpider
from pa11ycrawler.tests.helpers import (
    get_test_settings_dict,
    fake_response_from_file,
)


class Pa11ySpiderTest(TestCase):

    def setUp(self):
        super(Pa11ySpiderTest, self).setUp()
        settings = get_test_settings_dict()
        self.crawler = get_crawler(settings_dict=settings)
        self.spider = Pa11ySpider.from_crawler(self.crawler)

    @freeze_time("2016-04-04 17:37:43.323246")
    def test_parse_item(self):
        filename = '847310eb455f9ae37cb56962213c491d_2016-04-04T17:37:43.323246'
        response = fake_response_from_file('samples/page.html')
        results = self.spider.parse_item(response)  # pylint: disable=no-member
        self.assertEqual(results['url'], 'http://www.example.com')
        self.assertEqual(results['page_title'], u'Test Page \xc2\xae')
        self.assertEqual(results['filename'], filename)
        self.assertEqual(results['headers'], {'Cookies': ['somecookie=cookieval']})
        self.assertEqual(results['source'], '')

    def test_spider_from_crawler(self):
        self.assertTrue(hasattr(self.spider, 'crawler'))
        self.assertIs(self.spider.crawler, self.crawler)
        self.assertTrue(hasattr(self.spider, 'settings'))
        self.assertIs(self.spider.settings, self.crawler.settings)
