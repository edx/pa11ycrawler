import pytest
import json
from datetime import datetime
import scrapy
from scrapy.http.response.html import HtmlResponse
import textwrap
from freezegun import freeze_time
from urlobject import URLObject
from pa11ycrawler.spiders.edx import EdxSpider, load_pa11y_ignore_rules
try:
    from urllib.parse import parse_qs
except ImportError:
    from urlparse import parse_qs


CSRF_HEADER = (
    "csrftoken=2JH7ojWIMGDjWxSrdnp4Jkg0bGxaS3MV; "
    "expires=Fri, 25-Aug-2017 18:55:05 GMT; "
    "Max-Age=31449600; Path=/; secure"
)
LOGIN_HTML = textwrap.dedent("""
    <html>
      <head>
        <title>Sign in or Register</title>
      </head>
      <body>
        <h1>Sign In</h1>
        <form id="login">
          <input name="email">
          <input name="password">
          <input type="checkbox" name="remember">
        </form>
        <button>Create an account</button>
      </body>
    </html>
""")


def urls_are_equal(url1, url2):
    """
    Compare to URLs for equality, ignoring the ordering of non-ordered elements.
    """
    url1 = URLObject(url1)
    url2 = URLObject(url2)
    return (
        url1.without_query() == url2.without_query() and
        url1.query_multi_dict == url2.query_multi_dict
    )


def test_start_with_login():
    spider = EdxSpider(email="staff@example.com", password="edx")
    requests = list(spider.start_requests())
    assert len(requests) == 1
    request = requests[0]
    assert isinstance(request, scrapy.Request)
    expected_url = 'http://localhost:8000/login'
    assert urls_are_equal(request.url, expected_url)
    assert request.method == "GET"
    assert request.headers == {}
    assert request.callback


def test_start_with_login_callback():
    spider = EdxSpider(email="staff@example.com", password="edx")
    fake_response = HtmlResponse(
        url="http://localhost:8000/login",
        body=b"",
        encoding="utf-8",
        headers={"Set-Cookie": CSRF_HEADER},
    )
    requests = list(spider.after_initial_csrf(fake_response))

    assert len(requests) == 1
    request = requests[0]
    assert isinstance(request, scrapy.Request)
    expected_url = 'http://localhost:8000/user_api/v1/account/login_session/'
    assert urls_are_equal(request.url, expected_url)
    assert request.method == "POST"
    body = parse_qs(request.body.decode('utf8'))
    expected_body = {
        "email": ["staff@example.com"],
        "password": ["edx"],
    }
    assert body == expected_body
    assert request.headers == {
        b'Content-Type': [b'application/x-www-form-urlencoded'],
        b'X-Csrftoken': [b'2JH7ojWIMGDjWxSrdnp4Jkg0bGxaS3MV'],
    }
    assert request.callback


def test_start_with_auto_auth():
    spider = EdxSpider(email=None, password=None)
    requests = list(spider.start_requests())
    assert len(requests) == 1
    request = requests[0]
    assert isinstance(request, scrapy.Request)
    expected_url = 'http://localhost:8000/auto_auth?course_id=course-v1%3AedX%2BTest101%2Bcourse&staff=true'
    assert urls_are_equal(request.url, expected_url)
    assert request.method == "GET"
    assert request.headers == {
        b"Accept": [b"application/json"]
    }
    assert request.callback


def test_auto_auth_response(mocker):
    spider = EdxSpider(email=None, password=None)
    fake_result = {
        "email": "sparky@gooddog.woof",
        "password": "b4rkb4rkwo0f",
    }
    fake_response = HtmlResponse(
        url="http://localhost:8000/auto_auth",
        body=json.dumps(fake_result).encode('utf8'),
        encoding="utf-8",
    )

    assert spider.login_email == None
    assert spider.login_password == None
    requests = list(spider.after_auto_auth(fake_response))
    assert spider.login_email == "sparky@gooddog.woof"
    assert spider.login_password == "b4rkb4rkwo0f"

    assert len(requests) == 1
    request = requests[0]
    assert isinstance(request, scrapy.Request)
    expected_url = 'http://localhost:8000/api/courses/v1/blocks/?course_id=course-v1%3AedX%2BTest101%2Bcourse&depth=all&all_blocks=true'
    assert urls_are_equal(request.url, expected_url)
    assert request.method == "GET"
    assert request.headers == {}
    assert not request.callback


@freeze_time("2016-01-01")
def test_log_back_in():
    fake_request = scrapy.Request(
        url="http://localhost:8000/foo/bar"
    )
    fake_response = HtmlResponse(
        url="http://localhost:8000/login?next=/foo/bar",
        request=fake_request,
        body=LOGIN_HTML.encode("utf-8"),
        encoding="utf-8",
        headers={"Set-Cookie": CSRF_HEADER},
    )
    spider = EdxSpider(email="abc@def.com", password="xyz")

    requests = list(spider.parse_item(fake_response))

    assert len(requests) == 2
    request = requests[0]
    item = requests[1]
    expected_url = 'http://localhost:8000/user_api/v1/account/login_session/?next=%2Ffoo%2Fbar'
    assert urls_are_equal(request.url, expected_url)
    assert request.method == "POST"
    body = parse_qs(request.body.decode('utf8'))
    expected_body = {
        "email": ["abc@def.com"],
        "password": ["xyz"],
    }
    assert body == expected_body
    assert request.headers == {
        b'Content-Type': [b'application/x-www-form-urlencoded'],
        b'X-Csrftoken': [b'2JH7ojWIMGDjWxSrdnp4Jkg0bGxaS3MV'],
    }
    assert item == {
        'accessed_at': datetime(2016, 1, 1),
        'page_title': 'Sign in or Register',
        'request_headers': {},
        'url': 'http://localhost:8000/login?next=/foo/bar',
    }


def test_load_pa11y_rules_file(tmpdir):
    fake_rules = textwrap.dedent(u"""
      "*":
        - message: >-
            Check that the link text combined with programmatically determined
            link context identifies the purpose of the link.
          context: <a * href="#main">Skip to main content</a>
          type: notice
    """)
    rule_file = tmpdir / "ignore.yaml"
    rule_file.write_text(fake_rules, encoding="utf8")

    result = load_pa11y_ignore_rules(file=rule_file)

    expected_result = {
        "*": [{
            "message": (
                "Check that the link text combined with programmatically determined "
                "link context identifies the purpose of the link."
            ),
            "context": '<a * href="#main">Skip to main content</a>',
            "type": "notice",
        }]
    }
    assert result == expected_result


def test_load_pa11y_rules_none():
    assert load_pa11y_ignore_rules() == None

