"""
A spider that can crawl an Open edX instance.
"""
import os
import json
from datetime import datetime
from urlobject import URLObject
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from pa11ycrawler.items import A11yItem

AUTO_AUTH_PATH = "/auto_auth"
COURSE_BLOCKS_API_PATH = "/api/courses/v1/blocks"


class EdxSpider(CrawlSpider):
    "A Scrapy spider that can crawl an Open edX instance."
    name = 'edx'

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
            domain="localhost",
            port="8000",
            email=None,
            password=None,
            course_key="course-v1:edX+Test101+course",
            data_dir="data",
        ):  # noqa
        super(EdxSpider, self).__init__()

        self.login_email = email
        self.login_password = password
        self.domain = domain
        self.port = int(port)
        self.course_key = course_key
        self.data_dir = os.path.abspath(os.path.expanduser(data_dir))

        # set start URL based on course_key, which is the test course by default
        api_url = (
            URLObject("http://")
            .with_hostname(self.domain)
            .with_port(self.port)
            .with_path(COURSE_BLOCKS_API_PATH)
            .set_query_params(
                course_id=self.course_key,
                depth="all",
                all_blocks="true",
            )
        )
        self.start_urls = [api_url]
        self.allowed_domains = [domain]

    def start_requests(self):
        """
        Gets the spider started.
        If both `self.login_email` and `self.login_password` are set, this
        method generates requests from `self.start_urls`. If not, this method
        gets credentials using the "auto auth" feature, and *then* generates
        requests from `self.start_urls`.
        """
        if self.login_email and self.login_password:
            for url in self.start_urls:
                yield self.make_requests_from_url(url)
        else:
            self.logger.info(
                "email/password unset, fetching credentials via auto_auth"
            )
            auth_url = (
                URLObject("http://")
                .with_hostname(self.domain)
                .with_port(self.port)
                .with_path(AUTO_AUTH_PATH)
                .set_query_params(
                    staff='true',
                    course_id=self.course_key,
                )
            )
            # make sure to request a parseable JSON response
            yield scrapy.Request(
                auth_url,
                headers={b"Accept": b"application/json"},
                callback=self.parse_auto_auth,
            )

    def parse_auto_auth(self, response):
        """
        Parse the response from the "auto auth" feature.
        Once we have an email and password, move on to the
        `self.start_urls` list.
        """
        result = json.loads(response.body)
        self.login_email = result["email"]
        self.login_password = result["password"]
        msg = (
            "Obtained credentials via auto_auth! "
            "email={email} password={password}"
        ).format(**result)
        self.logger.info(msg)

        for url in self.start_urls:
            yield self.make_requests_from_url(url)

    def parse_item(self, response):
        """
        Get basic information about a page, so that it can be passed to the
        `pa11y` tool for further testing.

        @url https://www.google.com/
        @returns items 1 1
        @returns requests 0 0
        @scrapes url request_headers accessed_at page_title
        """
        # if we got redirected to a login page, then login
        if URLObject(response.url).path in ("/login", "/register"):
            yield self.make_login_request(response)

        title = response.xpath("//title/text()").extract_first().strip()
        # `response.request.headers` is a dictionary where the key is the
        # header name, and the value is a *list*, containing one item,
        # which is the header value. We need to get rid of this list, and just
        # have key-value pairs. (This list probably exists in case the same
        # header is sent multiple times, but that's not happening in this case,
        # and the list construct is getting in the way.)
        request_headers = {key: value[0] for key, value
                           in response.request.headers.items()}
        item = A11yItem(
            url=response.url,
            request_headers=request_headers,
            accessed_at=datetime.utcnow(),
            page_title=title,
        )
        yield item

    def make_login_request(self, response):
        """
        If the page wants me to log in, then I'll log in!
        """
        credentials = {
            "email": self.login_email,
            "password": self.login_password,
        }
        return scrapy.FormRequest.from_response(
            response,
            formdata=credentials
        )

    def after_login(self, response):
        """
        Check for a login error, then proceed as normal.
        """
        if "We couldn't sign you in." in response.body:
            self.logger.error("Credentials failed!")
            return

        for item in self.parse_item(response):
            yield item
