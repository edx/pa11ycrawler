# pylint: disable=missing-docstring
import json

from unittest import TestCase

from scrapy.utils.test import get_crawler
from scrapy.exceptions import DropItem

from pa11ycrawler.items import A11yItem
from pa11ycrawler.pipelines import Pa11yPipeline, DuplicatesPipeline
from pa11ycrawler.spiders.pa11y_spider import Pa11ySpider
from pa11ycrawler.tests.helpers import get_test_settings_dict


class BasePipelineTestCase(TestCase):

    pipeline = None

    def setUp(self):
        super(BasePipelineTestCase, self).setUp()
        settings = get_test_settings_dict(
            PA11YCRAWLER_CUSTOM_REPORTER_CLASS='pa11ycrawler.tests.helpers.NullReporter',
            PA11Y_REPORTER='1.0-json'
        )
        self.crawler = get_crawler(settings_dict=settings)
        self.spider = Pa11ySpider.from_crawler(self.crawler)
        self.item = A11yItem(
            url="http://example.com",
            headers={},
            filename='testing_testing_123',
            source='scraped page content',
        )


class Pa11yRunPipelineTestCase(BasePipelineTestCase):

    pipeline = Pa11yPipeline()

    def test_get_pa11y_settings(self):
        settings = self.pipeline.get_pa11y_settings(self.spider)
        expected_settings = [
            '--standard="WCAG2AA"',
            '--reporter="1.0-json"',
            '--level="notice"',
        ]
        self.assertEqual(settings, expected_settings)

    def test_process_item(self):
        process_item = self.pipeline.process_item(self.item, self.spider)
        results = json.loads(process_item['results'])
        self.assertFalse(results['isPerfect'])
        self.assertEqual(results['count']['total'], 3)
        self.assertEqual(results['count']['error'], 1)
        self.assertEqual(results['count']['warning'], 0)
        self.assertEqual(results['count']['notice'], 2)
        self.assertEqual(len(results['results']), 3)


class DuplicatesPipelineTestCase(BasePipelineTestCase):

    pipeline = DuplicatesPipeline()

    def test_process_item_seen(self):
        """
        Previously seen pages shouldn't be processed further.
        """
        with self.assertRaises(DropItem):
            self.pipeline.process_item(self.item, self.spider)

    def test_process_item_new(self):
        """
        Pages seen for the first time should be added to the 'seen' list
        and continue to be processed.
        """
        processed_item = self.pipeline.process_item(self.item, self.spider)
        self.assertIs(processed_item, self.item)
