"""
A spider that can crawl an instance of Open edX running locally.
"""
import os
from datetime import datetime
from urlobject import URLObject
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from pa11ycrawler.items import A11yItem

AUTO_AUTH_URL = "http://localhost:8003/auto_auth"
COURSE_BLOCKS_API_URL = "http://localhost:8003/api/courses/v1/blocks"


class EdxSpider(CrawlSpider):
    "A Scrapy spider that can crawl Open edX."
    name = 'local-edx'
    allowed_domains = ['localhost']
    start_urls = []

    rules = (
        Rule(
            LinkExtractor(
                deny=[
                    # don't crawl logout links
                    r"/logout/",
                    # don't crawl xblock links
                    r"://[^/]+/xblock/",
                    # don't crawl anything that returns an archive
                    r"\?_accept=application/x-tgz",
                ],
                unique=True,
            ),
            callback='parse_item',
            follow=True,
        ),
    )

    def __init__(
            self,
            course_key="course-v1:edX+Test101+course",
            data_dir="data",
        ):  # noqa
        # set start URL based on course_key, which is the test course by default
        api_url = URLObject(COURSE_BLOCKS_API_URL).set_query_params(
            course_id=course_key,
            depth="all",
            all_blocks="true",
        )
        auth_url = URLObject(AUTO_AUTH_URL).set_query_params(
            staff='true',
            course_id=course_key,
            redirect="true",
            redirect_to=api_url,
        )
        self.start_urls = [auth_url]

        super(EdxSpider, self).__init__()

        self.data_dir = os.path.abspath(os.path.expanduser(data_dir))

    def parse_item(self, response):
        """
        Get basic information about a page, so that it can be passed to the
        `pa11y` tool for further testing.

        @url https://www.google.com/
        @returns items 1 1
        @returns requests 0 0
        @scrapes url request_headers accessed_at page_title
        """
        title = response.xpath("//title/text()").extract_first().strip()
        item = A11yItem(
            url=response.url,
            request_headers=response.request.headers,
            accessed_at=datetime.utcnow(),
            page_title=title,
        )
        return item
