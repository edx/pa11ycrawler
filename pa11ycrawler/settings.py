# -*- coding: utf-8 -*-
"""
Scrapy settings for a11y project

For simplicity, this file contains only settings considered important or
commonly used. You can find more settings consulting the documentation:

    http://doc.scrapy.org/en/latest/topics/settings.html
    http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
    http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
"""

# Custom crawler settings --------------------------------------
# Note: PA11YCRAWLER_START_URLS must be set

PA11YCRAWLER_START_URLS = []
PA11YCRAWLER_ALLOWED_DOMAINS = []
PA11YCRAWLER_DENY_URL_MATCHER = []
PA11YCRAWLER_REPORTS_DIR = 'pa11ycrawler_reports'
PA11YCRAWLER_SAVE_SOURCE = False
PA11YCRAWLER_KEEP_EXISTING_REPORTS = False
PA11YCRAWLER_CUSTOM_REPORTER_CLASS = 'pa11ycrawler.reporter.Pa11yGenericReporter'

# The following items are pa11y settings -----------------------
# See: https://github.com/springernature/pa11y#command-line-interface

# -s, --standard <name>
# the accessibility standard to use:
# Section508, WCAG2A, WCAG2AA (default), WCAG2AAA
PA11Y_STANDARD = 'WCAG2AA'

# -r, --reporter <reporter>
# the reporter to use: cli (default), csv, html, json, 1.0-json
# The default for the crawler requires
# https://github.com/springernature/pa11y-reporter-1.0-json
PA11Y_REPORTER = 'html'

# -l, --level <level>
# the level of message to fail on (exit with code 2): error, warning, notice
PA11Y_LEVEL = 'notice'

# -T, --threshold <name>
# the number of individual errors, warnings, or notices
# to permit before failing
PA11Y_THRESHOLD = ''

# -i, --ignore <ignore>
# types and codes of messages to ignore, a repeatable value or separated by
# semi-colons (e.g. 'notice;warning')
PA11Y_IGNORE = ''

# -E, --hide-elements
# <hide> a CSS selector to hide elements from testing,
# selectors can be comma separated
PA11Y_HIDE_ELEMENTS = ''

# -R, --root-element <element>
# the root element for testing a subset of the document
PA11Y_ROOT_ELEMENT = ''

# -c, --config <path>
# a JSON or JavaScript config file
# Note that config can NOT be overridden. This is programatically created and
# and removed by the crawler in order to pass cookies/headers to pa11y.

# -p, --port <port> the port to run PhantomJS on
PA11Y_PORT = ''

# -t, --timeout <ms> the timeout in milliseconds
PA11Y_TIMEOUT = ''

# -w, --wait <ms> the time to wait before running tests in milliseconds
PA11Y_WAIT = ''

# -d, --debug output debug messages
PA11Y_DEBUG = False

# -H, --htmlcs <url> the URL or path to source HTML_CodeSniffer from
PA11Y_HTMLCS = ''

# -e, --phantomjs <path> the path to the phantomjs executable
PA11Y_PHANTOMJS = ''


# Other items you are likely to want to override ---------------
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
COOKIES_DEBUG = False
COOKIES_ENABLED = True
DEPTH_LIMIT = 2
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(name)s]: %(message)s'

# Don't override these or the crawler will surely break --------
BOT_NAME = 'pa11ycrawler'
SPIDER_MODULES = ['pa11ycrawler.spiders']
NEWSPIDER_MODULE = 'pa11ycrawler.spiders'
DEFAULT_ITEM_CLASS = 'pa11ycrawler.items.A11yItem'

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'pa11ycrawler.pipelines.DuplicatesPipeline': 200,
    'pa11ycrawler.pipelines.Pa11yPipeline': 300,
}
