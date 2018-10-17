# -*- coding: utf-8 -*-
import os
import pytest
import json
from datetime import datetime
import subprocess as sp
from scrapy.exceptions import DropItem, NotConfigured
from pa11ycrawler.pipelines import (
    DuplicatesPipeline, DropDRFPipeline, Pa11yPipeline
)
from pa11ycrawler.pipelines.pa11y import DEVNULL, load_pa11y_results
try:
    from StringIO import StringIO
except ImportError:  # Python 3
    from io import StringIO


def test_duplicates_pipeline():
    dup_pl = DuplicatesPipeline()
    spider = object()
    # first item: no problem
    item1 = {"url": "google.com"}
    processed1 = dup_pl.process_item(item1, spider)
    assert item1 == processed1

    # second item is different, so no problem
    item2 = {"url": "edx.org"}
    processed2 = dup_pl.process_item(item2, spider)
    assert item2 == processed2

    # third is the same as a previous, so raises an exception
    item3 = {"url": "google.com"}
    with pytest.raises(DropItem):
        dup_pl.process_item(item3, spider)

    # fourth is different, so no problem
    item4 = {"url": "edx.org/foo"}
    processed4 = dup_pl.process_item(item4, spider)
    assert item4 == processed4

    # fifth has other, different properties, but the URL is the same
    item5 = {"url": "edx.org/foo", "page_title": "TitleCase"}
    with pytest.raises(DropItem):
        dup_pl.process_item(item5, spider)


def test_duplicates_pipeline_querystring():
    dup_pl = DuplicatesPipeline()
    spider = object()
    item1 = {"url": "https://courses.edx.org/register?next=foo"}
    processed1 = dup_pl.process_item(item1, spider)
    assert item1 == processed1

    item2 = {"url": "https://courses.edx.org/register?next=bar"}
    with pytest.raises(DropItem):
        dup_pl.process_item(item2, spider)

    item3 = {"url": "https://courses.edx.org/register?foo=bar"}
    with pytest.raises(DropItem):
        dup_pl.process_item(item3, spider)

    item4 = {"url": "https://courses.edx.org/register"}
    with pytest.raises(DropItem):
        dup_pl.process_item(item4, spider)


def test_duplicates_pipeline_courseware_start():
    dup_pl = DuplicatesPipeline()
    spider = object()
    item1 = {"url": "https://courses.edx.org/courses/foo/courseware/bar/baz/"}
    processed1 = dup_pl.process_item(item1, spider)
    assert item1 == processed1

    item2 = {"url": "https://courses.edx.org/courses/foo/courseware/bar/baz/1"}
    with pytest.raises(DropItem):
        dup_pl.process_item(item2, spider)

    item3 = {"url": "https://courses.edx.org/courses/foo/courseware/bar/baz/2"}
    processed3 = dup_pl.process_item(item3, spider)
    assert item3 == processed3

    item4 = {"url": "https://courses.edx.org/courses/quux/courseware/bar/baz/1"}
    processed4 = dup_pl.process_item(item4, spider)
    assert item4 == processed4

    item5 = {"url": "https://courses.edx.org/courses/quux/courseware/bar/baz/"}
    with pytest.raises(DropItem):
        dup_pl.process_item(item5, spider)

    item6 = {"url": "https://courses.edx.org/courses/quux/courseware/bar/baz/6"}
    processed6 = dup_pl.process_item(item6, spider)
    assert item6 == processed6


def test_drf_pipeline():
    drf_pl = DropDRFPipeline()
    spider = object()

    with pytest.raises(DropItem):
        drf_pl.process_item({"url": "http://courses.edx.org/api/"}, spider)

    # non-api url is fine, though
    item = {"url": "http://courses.edx.org/course/whatever"}
    processed = drf_pl.process_item(item, spider)
    assert item == processed


def test_pa11y_happy_path(mocker, tmpdir):
    item = {
        "url": "http://courses.edx.org/fakepage",
        "page_title": "This is a Fake Page",
        "request_headers": {"Cookie": "nocookieforyou"},
        "accessed_at": datetime(2016, 8, 20, 14, 12, 45),
    }
    fake_pa11y_data = [{
        "message": "Check that the title element describes the document.",
        "code": "WCAG2AA.Principle2.Guideline2_4.2_4_2.H25.2",
        "type": "notice",
        "context": "<title>\t\nThis is a Fake Pa...</title>",
        "selector": "#fake > div",
    }]

    # setup
    data_dir = tmpdir.mkdir("data")
    spider = mocker.Mock(data_dir=str(data_dir), pa11y_ignore_rules=None)

    # fake subprocess: version
    mocker.patch("subprocess.check_call")

    # fake subprocess: run pa11y
    pa11y_process = mocker.Mock(name="run-Popen", returncode=None)
    def mock_communicate():
        pa11y_process.returncode = 2
        # returns both stdout and stderr
        return json.dumps(fake_pa11y_data).encode('utf8'), b""
    pa11y_process.communicate.side_effect = mock_communicate
    mock_Popen = mocker.patch("subprocess.Popen", return_value=pa11y_process)

    mock_tempfile = StringIO()
    mock_tempfile.name = "mockconfig.json"
    # stub out the `.close()` method, so that we can re-read this data
    # later in the test
    mock_tempfile.close = lambda: None
    mock_tempfile_ctor = mocker.patch(
        "tempfile.NamedTemporaryFile",
        return_value=mock_tempfile,
    )
    mock_remove = mocker.patch("os.remove")

    # test
    pa11y_pl = Pa11yPipeline()
    processed = pa11y_pl.process_item(item, spider)

    # check -------

    # item should be unchanged
    assert item == processed

    # pa11y should be called correctly
    mock_Popen.assert_called_with(
        ["node_modules/.bin/pa11y", "http://courses.edx.org/fakepage",
         "--config=mockconfig.json", "--include-notices",
         "--include-warnings", "--reporter=json"],
        shell=False, stdout=sp.PIPE, stderr=sp.PIPE
    )

    # title matcher didn't see a problem
    assert not spider.logger.error.called

    # one data file should be output correctly
    data_files = data_dir.listdir()
    assert len(data_files) == 1
    data_file = data_files[0]
    assert data_file.basename == 'c13d12d109449354e331b1b2f062dcb6.json'
    data_from_file = json.load(data_file)
    item["pa11y"] = fake_pa11y_data
    item["accessed_at"] = item["accessed_at"].isoformat()
    assert data_from_file == item

    # config file should be created and destroyed
    mock_tempfile.seek(0)
    pa11y_config = json.load(mock_tempfile)
    expected_config = {
        "headers": {
            "Cookie": "nocookieforyou",
        }
    }
    assert pa11y_config == expected_config
    mock_remove.assert_called_with("mockconfig.json")


def test_chrome_path_not_specified(monkeypatch):
    monkeypatch.setitem(os.environ, "PUPPETEER_SKIP_CHROMIUM_DOWNLOAD", "1")
    monkeypatch.delitem(os.environ, "PUPPETEER_EXECUTABLE_PATH")
    with pytest.raises(NotConfigured) as err:
        Pa11yPipeline()

    assert "Google Chrome is not installed" in err.value.args[0]


def test_chrome_not_installed(mocker, monkeypatch):
    monkeypatch.setitem(os.environ, "PUPPETEER_SKIP_CHROMIUM_DOWNLOAD", "1")
    monkeypatch.setitem(os.environ, "PUPPETEER_EXECUTABLE_PATH", "/usr/bin/google-chrome-stable")
    mock_check_call = mocker.patch(
        "subprocess.check_call", side_effect=(OSError, 0)
    )

    with pytest.raises(NotConfigured) as err:
        Pa11yPipeline()

    assert "Google Chrome is not installed" in err.value.args[0]

    mock_check_call.assert_called_with(
        [os.environ["PUPPETEER_EXECUTABLE_PATH"], "--version"],
        stdout=DEVNULL, stderr=DEVNULL,
    )


def test_pa11y_not_installed(mocker):
    mock_check_call = mocker.patch(
        "subprocess.check_call", side_effect=(0, OSError)
    )

    with pytest.raises(NotConfigured) as err:
        Pa11yPipeline()

    assert "pa11y is not installed" in err.value.args[0]

    mock_check_call.assert_called_with(
        ["node_modules/.bin/pa11y", "--version"],
        stdout=DEVNULL, stderr=DEVNULL,
    )


def test_pa11y_title_mismatch(mocker, tmpdir):
    item = {
        "url": "http://courses.edx.org/ponies",
        "page_title": u"Sparkly Ponies of Joy ☃",
        "request_headers": {"Cookie": "nocookieforyou"},
        "accessed_at": datetime(2016, 8, 20, 14, 12, 45),
    }
    fake_pa11y_data = [{
        "message": "Check that the title element describes the document.",
        "code": "WCAG2AA.Principle2.Guideline2_4.2_4_2.H25.2",
        "type": "notice",
        "typeCode": 3,
        "context": "<title>Evil Demons of Despa...</title>",
        "selector": "#hell > div > div:nth-child(7) > ul:nth-child(2)",
    }]

    # setup
    data_dir = tmpdir.mkdir("data")
    spider = mocker.Mock(data_dir=str(data_dir), pa11y_ignore_rules=None)

    # fake subprocess: version
    mocker.patch("subprocess.check_call")

    # fake subprocess: run pa11y
    pa11y_process = mocker.Mock(name="run-Popen", returncode=None)
    def mock_communicate():
        pa11y_process.returncode = 2
        # returns both stdout and stderr
        return json.dumps(fake_pa11y_data).encode('utf8'), b""
    pa11y_process.communicate.side_effect = mock_communicate
    mocker.patch("subprocess.Popen", return_value=pa11y_process)

    # stub out config file creation/removal
    mocker.patch("tempfile.NamedTemporaryFile")
    mocker.patch("os.remove")

    # test
    pa11y_pl = Pa11yPipeline()
    pa11y_pl.process_item(item, spider)

    # check
    expected_msg = (
        u'Parser mismatch! Scrapy saw full title "Sparkly Ponies of Joy ☃", '
        'Pa11y saw elided title "Evil Demons of Despa...".'
    )
    spider.logger.error.assert_called_with(expected_msg)


def test_pa11y_stats(mocker, tmpdir):
    item = {
        "url": "http://courses.edx.org/stats",
        "page_title": "Stats Collection for Dummies",
        "request_headers": {"Cookie": "nocookieforyou"},
        "accessed_at": datetime(2016, 8, 26, 14, 12, 45),
    }
    fake_pa11y_data = [
        {"type": "error", "context":""},
        {"type": "error", "context":""},
        {"type": "warning", "context":""},
        {"type": "notice", "context":""},
        {"type": "error", "context":""},
        {"type": "notice", "context":""},
        {"type": "warning", "context":""},
        {"type": "warning", "context":""},
        {"type": "notice", "context":""},
        {"type": "notice", "context":""},
        {"type": "warning", "context":""},
        {"type": "notice", "context":""},
    ]

    # setup
    data_dir = tmpdir.mkdir("data")
    spider = mocker.Mock(data_dir=str(data_dir), pa11y_ignore_rules=None)

    # fake subprocess: version
    mocker.patch("subprocess.check_call")

    # fake subprocess: run pa11y
    pa11y_process = mocker.Mock(name="run-Popen", returncode=None)
    def mock_communicate():
        pa11y_process.returncode = 2
        # returns both stdout and stderr
        return json.dumps(fake_pa11y_data).encode('utf8'), b""
    pa11y_process.communicate.side_effect = mock_communicate
    mocker.patch("subprocess.Popen", return_value=pa11y_process)

    # stub out config file creation/removal
    mocker.patch("tempfile.NamedTemporaryFile")
    mocker.patch("os.remove")

    # test
    pa11y_pl = Pa11yPipeline()
    pa11y_pl.process_item(item, spider)

    # check
    inc_value = spider.crawler.stats.inc_value
    inc_value.assert_any_call("pa11y/error", count=3, spider=spider)
    inc_value.assert_any_call("pa11y/warning", count=4, spider=spider)
    inc_value.assert_any_call("pa11y/notice", count=5, spider=spider)


def test_ignore_rules(mocker):
    fake_pa11y_data = [
        {"type": "error", "message": "you must construct additional pylons"},
        {"type": "error", "message": "we require more vespene gas"},
        {"type": "warning", "message": "our units are under attack"},
        {"type": "warning", "message": "SCVs are under attack"},
        {"type": "error", "message": "observers cannot attack"},
        {"type": "notice", "message": "construction finished"},
        {"type": "error", "message": "spawn more overlords"},
        {"type": "warning", "message": "vespene geyser exhausted"},
        {"type": "warning", "message": "mineral field depleted"},
    ]
    output = json.dumps(fake_pa11y_data).encode('utf8')
    ignore_rules = {
        "*": [
            {"message": "*overlords"}
        ],
        "/starcraft": [
            {"type": "notice"},
            {"message": "*vespene*"},
            {"message": "*attack*", "type": "warning"},
        ],
        "/vespene": [
            {"message": "*depleted*"},
        ]
    }
    spider = mocker.Mock(pa11y_ignore_rules=ignore_rules)
    url = "/starcraft"

    results = load_pa11y_results(output, spider, url)
    assert results == [
        {"type": "error", 'message': 'you must construct additional pylons'},
        {"type": "error", 'message': 'observers cannot attack'},
        {"type": "warning", 'message': 'mineral field depleted'},
    ]
