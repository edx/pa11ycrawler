import pytest
from optparse import OptionParser
from scrapy.crawler import CrawlerRunner
from scrapy.statscollectors import MemoryStatsCollector


@pytest.fixture
def mock_runner(mocker):
    """
    Return a function that builds a mock CrawlerRunner for use in testing
    scrapy commands.
    """
    def build_mock_runner(stats_value):
        """
        Return a mock CrawlerRunner containing a mocked Crawler instance.
        This Crawler's stats object will return the given stats_value for
        any queried stat.
        """
        CrawlCommandMock = mocker.patch('scrapy.commands.crawl.Command')

        StatsMock = mocker.patch('scrapy.statscollectors.MemoryStatsCollector')
        stats_instance = StatsMock.return_value
        stats_instance.get_value.return_value = stats_value

        CrawlerMock = mocker.patch('scrapy.crawler.Crawler')
        crawler_instance = CrawlerMock()
        settings = mocker.PropertyMock(return_value='foo')
        type(crawler_instance).settings = {
            'FAILURE_CATEGORIES': [
                'foo/ERROR',
                'bar/WARNING'
            ]
        }
        type(crawler_instance).stats = stats_instance

        RunnerMock = mocker.patch('scrapy.crawler.CrawlerRunner')
        runner_instance = RunnerMock()
        runner_instance.create_crawler.return_value = crawler_instance

        return runner_instance

    return build_mock_runner

def test_run_pass(mock_runner):
    """
    Simulate a test run with no errors and ensure the process exits with
    the proper exitcode.
    """
    runner_instance = mock_runner(stats_value=None)

    # we have to import TestCommand here rather than globally, to avoid
    # conflicting with the mocked scrapy.commands.crawl.Command
    from pa11ycrawler.commands.test import Command as TestCommand
    tc = TestCommand()
    tc.crawler_process = runner_instance
    tc.run(['edx'], {})
    assert tc.exitcode == 0

def test_run_failure(mock_runner):
    """
    Simulate a test run that yields a nonzero error stat count and ensure
    the process exits with the proper exitcode.
    """
    runner_instance = mock_runner(stats_value=3)

    from pa11ycrawler.commands.test import Command as TestCommand
    tc = TestCommand()
    tc.crawler_process = runner_instance
    tc.run(['edx'], {})
    assert tc.exitcode == 1

def test_passthrough_add_options_called(mocker):
    """
    Ensure that the test command passes through its add_options call
    to scrapy.commands.crawl.Command.
    """
    CrawlCommandMock = mocker.patch('scrapy.commands.crawl.Command')
    crawl_instance = CrawlCommandMock()
    add_options_spy = mocker.spy(crawl_instance, 'add_options')

    from pa11ycrawler.commands.test import Command as TestCommand
    tc = TestCommand()

    tc.existing_crawl_command = crawl_instance
    fake_parser = OptionParser()
    tc.add_options(fake_parser)

    assert crawl_instance.add_options.call_count == 1
    add_options_spy.assert_called_with(fake_parser)

def test_passthrough_process_options_called(mocker):
    """
    Ensure that the test command passes through its process_options call
    to scrapy.commands.crawl.Command.
    """
    CrawlCommandMock = mocker.patch('scrapy.commands.crawl.Command')
    crawl_instance = CrawlCommandMock()
    process_options_spy = mocker.spy(crawl_instance, 'process_options')

    from pa11ycrawler.commands.test import Command as TestCommand
    tc = TestCommand()

    tc.existing_crawl_command = crawl_instance
    fake_args = {'foo': 'bar'}
    fake_opts = ['baz', 'quux']
    tc.process_options(fake_args, fake_opts)

    assert crawl_instance.process_options.call_count == 1
    process_options_spy.assert_called_with(fake_args, fake_opts)
