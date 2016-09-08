"""
A spider that can crawl an Open edX instance.
"""
import os
import re
import json
from datetime import datetime
from path import Path
import yaml
import requests
from urlobject import URLObject
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from pa11ycrawler.items import A11yItem

LOGIN_HTML_PATH = "/login"
LOGIN_API_PATH = "/user_api/v1/account/login_session/"
AUTO_AUTH_PATH = "/auto_auth"
COURSE_BLOCKS_API_PATH = "/api/courses/v1/blocks/"
LOGIN_FAILURE_MSG = "We couldn't sign you in."


def get_csrf_token(response):
    """
    Extract the CSRF token out of the "Set-Cookie" header of a response.
    """
    cookie_headers = [
        h.decode('ascii') for h in response.headers.getlist("Set-Cookie")
    ]
    if not cookie_headers:
        return None
    csrf_headers = [
        h for h in cookie_headers if h.startswith("csrftoken=")
    ]
    if not csrf_headers:
        return None
    match = re.match("csrftoken=([^ ;]+);", csrf_headers[-1])
    return match.group(1)


def load_pa11y_ignore_rules(file=None, url=None):  # pylint: disable=redefined-builtin
    """
    Load the pa11y ignore rules from the given file or URL.
    """
    if not file and not url:
        return None

    if file:
        file = Path(file)
        if not file.isfile():
            msg = (
                "pa11y_ignore_rules_file specified, "
                "but file does not exist! {file}"
            ).format(file=file)
            raise ValueError(msg)
        return yaml.safe_load(file.text())

    # must be URL
    resp = requests.get(url)
    if not resp.ok:
        msg = (
            "pa11y_ignore_rules_url specified, "
            "but failed to fetch URL. status={status}"
        ).format(status=resp.status_code)
        err = RuntimeError(msg)
        err.response = resp
        raise err
    return yaml.safe_load(resp.text)


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
            http_user=None,
            http_pass=None,
            course_key="course-v1:edX+Test101+course",
            pa11y_ignore_rules_file=None,
            pa11y_ignore_rules_url=None,
            data_dir="data",
        ):  # noqa
        super(EdxSpider, self).__init__()

        self.login_email = email
        self.login_password = password
        self.domain = domain
        self.port = int(port)
        self.course_key = course_key
        self.http_user = http_user
        self.http_pass = http_pass
        self.data_dir = os.path.abspath(os.path.expanduser(data_dir))
        self.pa11y_ignore_rules = load_pa11y_ignore_rules(
            file=pa11y_ignore_rules_file, url=pa11y_ignore_rules_url,
        )

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
        If both `self.login_email` and `self.login_password` are set,
        this method generates a request to login with those credentials.
        Otherwise, this method generates a request to go to the "auto auth"
        page and get credentials from there. Either way, this method
        doesn't actually generate requests from `self.start_urls` -- that is
        handled by the `after_initial_login()` and `after_auto_auth()`
        methods.
        """
        if self.login_email and self.login_password:
            login_url = (
                URLObject("http://")
                .with_hostname(self.domain)
                .with_port(self.port)
                .with_path(LOGIN_HTML_PATH)
            )
            yield scrapy.Request(
                login_url,
                callback=self.after_initial_csrf,
            )
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
            headers = {
                b"Accept": b"application/json",
            }
            yield scrapy.Request(
                auth_url,
                headers=headers,
                callback=self.after_auto_auth,
            )

    def after_initial_csrf(self, response):
        """
        This method is called *only* if the crawler is started with an
        email and password combination.
        In order to log in, we need a CSRF token from a GET request. This
        method takes the result of a GET request, extracts the CSRF token,
        and uses it to make a login request. The response to this login
        request will be handled by the `after_initial_login` method.
        """
        login_url = (
            URLObject("http://")
            .with_hostname(self.domain)
            .with_port(self.port)
            .with_path(LOGIN_API_PATH)
        )
        credentials = {
            "email": self.login_email,
            "password": self.login_password,
        }
        headers = {
            b"X-CSRFToken": get_csrf_token(response),
        }
        yield scrapy.FormRequest(
            login_url,
            formdata=credentials,
            headers=headers,
            callback=self.after_initial_login,
        )

    def after_initial_login(self, response):
        """
        This method is called *only* if the crawler is started with an
        email and password combination.
        It verifies that the login request was successful,
        and then generates requests from `self.start_urls`.
        """
        if "We couldn't sign you in." in response.text:
            self.logger.error("Credentials failed!")
            return

        self.logger.info("successfully completed initial login")
        for url in self.start_urls:
            yield self.make_requests_from_url(url)

    def after_auto_auth(self, response):
        """
        This method is called *only* if the crawler is started without an
        email and password combination. It parses the response from the
        "auto auth" feature, and saves the email and password combination.
        Then it generates requests from `self.start_urls`.
        """
        result = json.loads(response.text)
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
        if URLObject(response.url).path == LOGIN_HTML_PATH:
            reqs = self.handle_unexpected_redirect_to_login_page(response)
            for req in reqs:
                yield req

        title = response.xpath("//title/text()").extract_first()
        if title:
            title = title.strip()

        # `response.request.headers` is a dictionary where the key is the
        # header name, and the value is a *list*, containing one item,
        # which is the header value. We need to get rid of this list, and just
        # have key-value pairs. (This list probably exists in case the same
        # header is sent multiple times, but that's not happening in this case,
        # and the list construct is getting in the way.)
        #
        # We also need to convert bytes to ASCII. In practice, headers can
        # only contain ASCII characters: see
        # http://stackoverflow.com/questions/5423223/how-to-send-non-english-unicode-string-using-http-header
        request_headers = {key.decode('ascii'): value[0].decode('ascii')
                           for key, value
                           in response.request.headers.items()}
        item = A11yItem(
            url=response.url,
            request_headers=request_headers,
            accessed_at=datetime.utcnow(),
            page_title=title,
        )
        yield item

    def handle_unexpected_redirect_to_login_page(self, response):
        """
        This method is called if the crawler has been unexpectedly logged out.
        If that happens, and the crawler requests a page that requires a
        logged-in user, the crawler will be redirected to a login page,
        with the originally-requested URL as the `next` query parameter.

        This method simply causes the crawler to log back in using the saved
        email and password credentials. We rely on the fact that the login
        page will redirect the user to the URL in the `next` query parameter
        if the login is successful -- this will allow the crawl to resume
        where it left off.

        This is method is very much like the `get_initial_login()` method,
        but the callback is `self.after_login` instead of
        `self.after_initial_login`.
        """
        next_url = URLObject(response.url).query_dict.get("next")
        login_url = (
            URLObject("http://")
            .with_hostname(self.domain)
            .with_port(self.port)
            .with_path(LOGIN_API_PATH)
        )
        if next_url:
            login_url = login_url.set_query_param("next", next_url)

        credentials = {
            "email": self.login_email,
            "password": self.login_password,
        }
        headers = {
            b"X-CSRFToken": get_csrf_token(response),
        }
        yield scrapy.FormRequest(
            login_url,
            formdata=credentials,
            headers=headers,
            callback=self.after_login,
        )

    def after_login(self, response):
        """
        Check for a login error, then proceed as normal.
        This is very much like the `after_initial_login()` method, but
        it searches for links in the response instead of generating
        requests from `self.start_urls`.
        """
        if LOGIN_FAILURE_MSG in response.text:
            self.logger.error("Credentials failed!")
            return

        # delegate to the `parse_item()` method, which handles normal responses.
        for item in self.parse_item(response):
            yield item
