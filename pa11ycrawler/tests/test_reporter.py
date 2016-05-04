# pylint: disable=missing-docstring
import json
import os
import shutil

from unittest import TestCase

from scrapy.utils.test import get_crawler

from pa11ycrawler.items import A11yItem
from pa11ycrawler.reporter import HtmlReporter
from pa11ycrawler.spiders.pa11y_spider import Pa11ySpider
from pa11ycrawler.tests.helpers import get_test_settings_dict


SAMPLE_RESULTS = [
    {
        'message': 'msg1',
        'code': 'WCAG2AA.Principle3.Guideline3_2.3_2_1.G107',
        'type': 'notice',
        'html': 'html1'
    },
    {
        'message': 'msg2',
        'code': 'WCAG2AA.Principle2.Guideline2_4.2_4_4.H77,H78,H79,H80,H81',
        'type': 'error',
        'html': 'html2'
    },
    {
        'message': 'msg3',
        'code': 'WCAG2AA.Principle1.Guideline1_1.1_1_1.G94.Image',
        'type': 'notice',
        'html': 'html3'
    },
    {
        'message': 'msg4',
        'code': 'unknownpattern_for_code',
        'type': 'notice',
        'html': 'html4'
    },
]


class BaseReporterTestCase(TestCase):
    def setUp(self):
        super(BaseReporterTestCase, self).setUp()
        settings = get_test_settings_dict(
            PA11Y_REPORTER='1.0-json'
        )
        crawler = get_crawler(settings_dict=settings)
        spider = Pa11ySpider.from_crawler(crawler)
        self.reporter = spider.a11y_reporter  # pylint: disable=no-member
        self.results = json.dumps({
            'count': {
                'notice': 2,
                'total': 3,
                'warning': 0,
                'error': 1,
            },
            'results': SAMPLE_RESULTS,
            'isPerfect': False,
        })
        self.item = A11yItem(
            url="http://example.com",
            page_title="Test Page",
            headers={},
            filename='testing_testing_123',
            source='scraped page content',
            results=self.results
        )

        self.results_file = os.path.join(
            self.reporter.results_dir,
            self.item['filename'] + '.1.0.json'
        )

        self.addCleanup(self.cleanup)

    def cleanup(self):
        shutil.rmtree(self.reporter.reports_dir)

    def test_reporter(self):
        self.reporter.pre_process_reports()
        self.reporter.add_results(self.item)
        self.reporter.post_process_reports()

        with open(self.reporter.results_map_file, 'r') as results_map:
            expected = json.dumps({
                "http://example.com": {
                    "page_title": "Test Page",
                    "filename": "testing_testing_123",
                }
            })
            self.assertEqual(results_map.read(), expected)

        with open(self.results_file, 'r') as results:
            self.assertEqual(results.read(), self.results)

    def test_keep_existing(self):
        self.reporter.pre_process_reports()
        self.reporter.add_results(self.item)
        self.reporter.settings.frozen = False
        self.reporter.settings.set('PA11YCRAWLER_KEEP_EXISTING_REPORTS', True)
        self.reporter.pre_process_reports()
        self.assertTrue(os.path.isfile(self.results_file))

    def test_save_html(self):
        self.reporter.settings.frozen = False
        self.reporter.settings.set('PA11YCRAWLER_SAVE_SOURCE', True)
        self.reporter.pre_process_reports()
        self.reporter.add_results(self.item)
        source_file = os.path.join(
            self.reporter.source_dir,
            self.item['filename'] + '.html'
        )
        self.assertTrue(os.path.isfile(source_file))


class HtmlReporterTestCase(TestCase):

    def setUp(self):
        super(HtmlReporterTestCase, self).setUp()
        settings = get_test_settings_dict(PA11Y_REPORTER='1.0-json')
        self.reporter = HtmlReporter(settings)
        results = json.dumps({
            'count': {
                'notice': 2,
                'total': 3,
                'warning': 0,
                'error': 1,
            },
            'results': SAMPLE_RESULTS,
            'isPerfect': False,
        })

        if not os.path.exists(self.reporter.results_dir):
            os.makedirs(self.reporter.results_dir)

        results_file = os.path.join(self.reporter.results_dir, '1234.1.0.json')
        with open(results_file, 'w') as results_file_opened:
            results_file_opened.write(results)

        results_map = json.dumps({
            'http://example.com': {
                'filename': '1234',
                'page_title': 'test',
            }
        })
        with open(self.reporter.results_map_file, 'w') as results_map_file:
            results_map_file.write(results_map)

        self.html_results_file = os.path.join(self.reporter.html_dir, '1234.html')
        self.html_summary_by_code_file = os.path.join(self.reporter.html_dir, 'summary_by_code.html')
        self.html_index_file = os.path.join(self.reporter.html_dir, 'index.html')

        self.addCleanup(self.cleanup)

    def cleanup(self):
        shutil.rmtree(self.reporter.reports_dir)

    def test_make_html(self):
        self.reporter.make_html()
        expected_summary = {
            'pageResults': {
                'http://example.com': {
                    'notice': 2,
                    'warning': 0,
                    'page_title': 'test',
                    'error': 1,
                    'total': 3,
                    'filename': '1234',
                },
            },
            'overallCount': {
                'notice': 2,
                'total': 3,
                'warning': 0,
                'pages_affected': 1,
                'error': 1,
            },
        }
        self.assertEqual(expected_summary, self.reporter.summary)

        expected_summary_by_code = {
            'WCAG2AA.Principle2.Guideline2_4.2_4_4.H77,H78,H79,H80,H81': {
                'message': 'msg2',
                'type': 'error',
                'pages': set([('test', 'http://example.com')]),
            },
            'unknownpattern_for_code': {
                'message': 'msg4',
                'type': 'notice',
                'pages': set([('test', 'http://example.com')]),
            },
            'WCAG2AA.Principle1.Guideline1_1.1_1_1.G94.Image': {
                'message': 'msg3',
                'type': 'notice',
                'pages': set([('test', 'http://example.com')]),
            },
            'WCAG2AA.Principle3.Guideline3_2.3_2_1.G107': {
                'message': 'msg1',
                'type': 'notice',
                'pages': set([('test', 'http://example.com')]),
            },
        }
        self.assertEqual(expected_summary_by_code, self.reporter.summary_by_code)

        self.assertTrue(os.path.isfile(self.html_results_file))
        self.assertTrue(os.path.isfile(self.html_index_file))
        self.assertTrue(os.path.isfile(self.html_summary_by_code_file))
