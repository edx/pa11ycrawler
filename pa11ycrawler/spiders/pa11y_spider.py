# -*- coding: utf-8 -*-
"""
Pa11ySpider
"""
import hashlib

from datetime import datetime
from pydoc import locate

from lxml.html import fromstring
from scrapy import signals
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.xlib.pydispatch import dispatcher

from pa11ycrawler.items import A11yItem


class Pa11ySpider(CrawlSpider):
    """
    CrawlSpider subclass for checking accessibility on a page.
    """
    name = 'pa11y'

    def __init__(self, *_args, **_kwargs):
        settings = self.settings
        self.start_urls = settings.get('PA11YCRAWLER_START_URLS')
        self.allowed_domains = settings.get('PA11YCRAWLER_ALLOWED_DOMAINS')
        deny_url_matcher = settings.get('PA11YCRAWLER_DENY_URL_MATCHER')
        self.rules = (
            Rule(
                LinkExtractor(deny=deny_url_matcher, unique=True),
                callback='parse_item',
                follow=True
            ),
        )

        # Note this needs to be called _after_ the start_urls,
        # allowed_domains, and rules are pulled from settings.
        super(Pa11ySpider, self).__init__()

        # Other things can be done after the parent's init has been called
        reporter_class = locate(settings.get('PA11YCRAWLER_CUSTOM_REPORTER_CLASS'))
        self.a11y_reporter = reporter_class(settings)
        self.save_source = settings.get('PA11YCRAWLER_SAVE_SOURCE')

        dispatcher.connect(self.spider_opened_handler, signals.spider_opened)
        dispatcher.connect(self.spider_closed_handler, signals.spider_closed)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """
        Used to provide the Pa11ySpider the crawler settings.
        """
        crawler.spidercls.settings = crawler.settings
        return super(Pa11ySpider, cls).from_crawler(crawler, *args, **kwargs)

    def spider_opened_handler(self):
        """
        Called when the spider is opened, before it begins crawling.
        """
        self.a11y_reporter.pre_process_reports()

    def spider_closed_handler(self):
        """
        Called just before the spider is closed, after it is done crawling.
        """
        self.a11y_reporter.post_process_reports()

    def parse_item(self, response):
        """
        Adds initial response information to an A11yItem.
        """
        now = datetime.utcnow().isoformat()
        hashed_url = hashlib.md5(unicode(response.url)).hexdigest()
        filename = '_'.join([hashed_url, now])
        title = fromstring(response.body).findtext('.//title')

        item = A11yItem(
            url=response.url,
            page_title=title,
            filename=filename,
            headers=response.request.headers,
            source=response.body if self.save_source else '',
        )
        self.logger.debug('ITEM: %s', item)
        return item
