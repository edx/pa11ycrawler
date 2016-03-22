# pylint: disable=missing-docstring
import argparse

from unittest import TestCase

from mock import patch, call

from pa11ycrawler.settings_helpers import get_default_settings
from pa11ycrawler.cmdline import (
    cli,
    run,
    gen_html_reports,
    get_flag_args,
    args_to_settings,
)


class CmdlineTestCase(TestCase):

    def test_cli(self):
        parser = cli()
        # These should parse without erroring
        parser.parse_args(['run', 'http://localhost:8000'])
        parser.parse_args(['json-to-html', '--pa11ycrawler-reports-dir', 'test'])

    @patch('pa11ycrawler.cmdline.CrawlerProcess')
    @patch('pa11ycrawler.cmdline.Pa11ySpider')
    def test_run(self, mock_spider, mock_crawler):
        settings = get_default_settings()
        run(settings)
        calls = [
            call(settings),
            call().crawl(mock_spider),
            call().start()
        ]
        mock_crawler.assert_has_calls(calls)

    @patch('pa11ycrawler.cmdline.HtmlReporter')
    def test_gen_html_reports(self, mock_reporter):
        settings = get_default_settings()
        gen_html_reports(settings)
        calls = [call().make_html()]
        mock_reporter.assert_has_calls(calls)

    def test_get_flag_args(self):
        # Given an int
        int_flag, int_flag_kwargs = get_flag_args('SETTING_NAME', 3)
        self.assertEqual(int_flag[0], '--setting-name')
        self.assertIs(int_flag_kwargs.get('type'), int)
        self.assertIsNone(int_flag_kwargs.get('nargs'))

        # Given a str
        _str_flag, str_flag_kwargs = get_flag_args('SETTING_NAME', '3')
        self.assertIs(str_flag_kwargs.get('type'), str)
        self.assertIsNone(str_flag_kwargs.get('nargs'))

        # Given a bool
        _bool_flag, bool_flag_kwargs = get_flag_args('SETTING_NAME', False)
        self.assertIs(bool_flag_kwargs.get('type'), bool)
        self.assertIsNone(bool_flag_kwargs.get('nargs'))

        # Given a dict
        _dict_flag, dict_flag_kwargs = get_flag_args('SETTING_NAME', {'a': 1, 'b': 2})
        self.assertIs(dict_flag_kwargs.get('type'), dict)
        self.assertIsNone(dict_flag_kwargs.get('nargs'))

        # Given a list
        _list_flag, list_flag_kwargs = get_flag_args('SETTING_NAME', [1, 2, 3])
        self.assertIsNone(list_flag_kwargs.get('type'))
        self.assertEqual(list_flag_kwargs.get('nargs'), '*')

        # Given a tuple
        _tuple_flag, tuple_flag_kwargs = get_flag_args('SETTING_NAME', (1, 2, 3))
        self.assertIsNone(tuple_flag_kwargs.get('type'))
        self.assertEqual(tuple_flag_kwargs.get('nargs'), '*')

    def test_args_to_settings(self):
        parser = argparse.ArgumentParser(prog='testpa11ycrawler')
        parser.add_argument('PA11YCRAWLER_START_URLS', nargs='+')
        parser.add_argument(
            '--pa11ycrawler-allowed-domains',
            dest='PA11YCRAWLER_ALLOWED_DOMAINS',
            nargs='*'
        )
        parser.add_argument(
            '--pa11y-reporter',
            dest='PA11Y_REPORTER',
            type=str
        )
        sample_args = parser.parse_args([
            'http://localhost:8000', 'http://localhost:8001',
            '--pa11ycrawler-allowed-domains', 'localhost',
            '--pa11y-reporter', 'csv',
        ])
        expected_settings = {
            'PA11YCRAWLER_START_URLS': [
                'http://localhost:8000',
                'http://localhost:8001',
            ],
            'PA11YCRAWLER_ALLOWED_DOMAINS': ['localhost'],
            'PA11Y_STANDARD': 'WCAG2AA',
            'PA11Y_REPORTER': 'csv',
        }

        settings = args_to_settings(sample_args)
        for key, value in expected_settings.iteritems():
            self.assertEqual(settings.attributes[key].value, value)
