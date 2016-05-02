#!/usr/bin/python
"""
The command line interface for pa11ycrawler.
"""
import argparse
import logging

from textwrap import dedent

from scrapy.crawler import CrawlerProcess

from pa11ycrawler.reporter import HtmlReporter
from pa11ycrawler.settings_helpers import (
    is_pa11y_setting,
    is_pa11ycrawler_setting,
    get_default_settings,
)
from pa11ycrawler.spiders.pa11y_spider import Pa11ySpider


# ------------ Main CLI ------------


def cli():
    """
    Returns the main CLI parser.
    """
    parser = argparse.ArgumentParser(prog='pa11ycrawler')
    subparsers = parser.add_subparsers(title='commands')
    run_cli(subparsers)
    json_to_html_cli(subparsers)
    return parser

# ------------ "run" CLI -----------


def run_cli(subparsers):
    """
    Creates the parser for the `run` command
    """
    run_usage = dedent('''pa11ycrawler run [options] url [url ...]

    ---------------------------------------------------------------
    NOTE: This only documents a haldful of the possible options.
    More documentation can be found for the following categories:

    CUSTOM SCRAPY SETTINGS:
    ** Implemented for pa11ycrawler. (e.g. not found in Scrapy docs.)
    ** All options documented below.
    ** Most likely, these will need to be set when running crawler.

    PA11Y SETTINGS:
    ** All options documented below. More details can be found at
       https://github.com/springernature/pa11y#command-line-interface

    STANDARD SCRAPY SETTINGS:
    ** http://doc.scrapy.org/en/latest/topics/settings.html
    ** These can be set using typical flag formatting. For example,
       --depth-limit=2 will set the DEPTH_LIMIT setting to 2.
    ---------------------------------------------------------------
    ''')

    parser_run = subparsers.add_parser(
        'run',
        usage=run_usage,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Run the crawler, checking accessibility along the way!"
    )
    parser_run.set_defaults(func=run)
    parser_run.add_argument(
        'PA11YCRAWLER_START_URLS',
        metavar='url',
        nargs='+',
        help='URL(s) to crawl'
    )

    custom_group = parser_run.add_argument_group('custom crawler options')
    pa11y_group = parser_run.add_argument_group('pa11y options')
    scrapy_group = parser_run.add_argument_group('scrapy options')

    settings = get_default_settings()
    keys = settings.attributes.keys()
    keys.sort()

    for key in keys:
        if key == 'PA11YCRAWLER_START_URLS':
            continue

        flag_args, flag_kwargs = get_flag_args(key, settings.attributes[key].value)

        if is_pa11ycrawler_setting(key):
            custom_group.add_argument(*flag_args, **flag_kwargs)
        elif is_pa11y_setting(key):
            pa11y_group.add_argument(*flag_args, **flag_kwargs)
        else:
            flag_kwargs['help'] = argparse.SUPPRESS
            scrapy_group.add_argument(*flag_args, **flag_kwargs)


def run(settings):
    """
    Runs the pa11ycrawler.
    """
    print 'Running pa11ycrawler...'
    process = CrawlerProcess(settings)
    process.crawl(Pa11ySpider)
    process.start()  # this will block until crawling is finished


# ------- "json-to-html" CLI -------

def json_to_html_cli(subparsers):
    """
    Creates the parser for the `json-to-html` command
    """
    usage_str = dedent('''pa11ycrawler json-to-html [options]

    ---------------------------------------------------------------
    NOTE: this only works if you run the crawler using the flag
          --pa11y-reporter="1.0-json" first
    ---------------------------------------------------------------
    ''')

    parser_html_reports = subparsers.add_parser(
        'json-to-html',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        usage=usage_str,
        help=(
            'Produce html reports from the previous crawl. NOTE: Must use '
            '`pa11ycrawler run --pa11y-reporter="1.0-json"` first.'
        )
    )

    settings = get_default_settings()
    keys = [
        'PA11YCRAWLER_REPORTS_DIR',
        'PA11YCRAWLER_KEEP_EXISTING_REPORTS',
        'LOG_LEVEL',
    ]

    for key in keys:
        flag_args, flag_kwargs = get_flag_args(key, settings.attributes[key].value)
        parser_html_reports.add_argument(*flag_args, **flag_kwargs)

    parser_html_reports.set_defaults(func=gen_html_reports)


def gen_html_reports(settings):
    """
    Generates html reports from the 1.0-json formatted reports.
    """
    print "Generating html reports..."
    reporter = HtmlReporter(settings)
    reporter.make_html()


# --------- helper methods ---------

def get_flag_args(key, setting):
    """
    Returns the arguments for the settings options so that they are
    parsed as the correct type.
    """
    flag = "--" + key.lower().replace('_', '-')
    args = [flag]
    kwargs = {
        'dest': key,
        'default': setting,
    }

    if isinstance(setting, list):
        kwargs['nargs'] = '*'
        kwargs['help'] = '(default: %(default)s) (type: list)'
    elif isinstance(setting, tuple):
        kwargs['nargs'] = '*'
        kwargs['help'] = '(default: %(default)s) (type: tuple)'
    else:
        kwargs['type'] = type(setting)
        kwargs['help'] = '(default: %(default)s) (type: %(type)s)'

    return args, kwargs


def args_to_settings(args):
    """
    Takes the parsed arguments, and translates them back into settings.
    Returns the settings.
    """
    settings = get_default_settings()
    for arg_name, arg_value in vars(args).iteritems():
        if arg_value and arg_name != 'func':
            settings.set(arg_name, arg_value)

    return settings


def main():
    """
    Gets the parser, parses the args, and calls the specified function.
    """
    parser = cli()
    args = parser.parse_args()
    settings = args_to_settings(args)
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"',
        level=settings.get('LOG_LEVEL')
    )
    args.func(settings)


if __name__ == "__main__":
    main()
