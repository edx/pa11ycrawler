"""
Helpers methods for tests
"""
import os

from scrapy.http import Response, Request

from pa11ycrawler.reporter import ReporterBaseClass, Pa11yAbstractSpiderReporter
from pa11ycrawler.settings_helpers import get_default_settings


class NullReporter(ReporterBaseClass, Pa11yAbstractSpiderReporter):
    """
    A reporter class that doesn't do anything.
    Used for testing methods that have reporting as a side-effect.
    """
    def add_results(self, item):
        pass

    def pre_process_reports(self):
        pass

    def post_process_reports(self):
        pass


def get_test_settings_dict(**kwargs):
    """
    Returns a dict representing the default settings.

    To override a default, pass the updated value as a kwarg.
    Example:
        get_test_settings_dict(PA11YCRAWLER_START_URLS=['example.com'])
    """
    settings = get_default_settings()

    settings_dict = {}
    for key, attr in settings.attributes.iteritems():
        settings_dict[key] = kwargs.get(key, attr.value)

    settings_dict['PA11YCRAWLER_REPORTS_DIR'] = 'test_root'

    return settings_dict


def fake_response_from_file(file_name, url=None):
    """
    Create a Scrapy fake HTTP response from a HTML file
    @param file_name: The relative filename from the responses directory,
                      but absolute paths are also accepted.
    @param url: The URL of the response.
    returns: A scrapy HTTP response which can be used for unittesting.
    """
    if not url:
        url = 'http://www.example.com'

    request = Request(url=url, headers={"cookies": "somecookie=cookieval"})
    if not file_name[0] == '/':
        responses_dir = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(responses_dir, file_name)
    else:
        file_path = file_name

    file_content = open(file_path, 'r').read()

    response = Response(
        url=url,
        request=request,
        body=file_content
    )
    response.encoding = 'utf-8'
    return response
