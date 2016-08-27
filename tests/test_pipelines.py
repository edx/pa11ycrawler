import pytest
import json
from datetime import datetime
import subprocess as sp
from scrapy.exceptions import DropItem, NotConfigured
from pa11ycrawler.pipelines import (
    DuplicatesPipeline, DropDRFPipeline, Pa11yPipeline, DEVNULL
)
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


def test_duplicates_pipeline_next():
    dup_pl = DuplicatesPipeline()
    spider = object()
    item1 = {"url": "https://courses.edx.org/register?next=foo"}
    item2 = {"url": "https://courses.edx.org/register?next=bar"}
    dup_pl.process_item(item1, spider)
    with pytest.raises(DropItem):
        dup_pl.process_item(item2, spider)


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
    fake_pa11y_data = {
        "results": [{
            "message": "Check that the title element describes the document.",
            "code": "WCAG2AA.Principle2.Guideline2_4.2_4_2.H25.2",
            "type": "notice",
            "html": "<title>\t\nThis is a Fake Pa...</title>"
        }]
    }

    # setup
    data_dir = tmpdir.mkdir("data")
    spider = mocker.Mock(data_dir=str(data_dir))

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
         "--config=mockconfig.json", "--reporter=1.0-json"],
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
    fake_pa11y_data.update(item)
    fake_pa11y_data["accessed_at"] = fake_pa11y_data["accessed_at"].isoformat()
    assert data_from_file == fake_pa11y_data

    # config file should be created and destroyed
    mock_tempfile.seek(0)
    pa11y_config = json.load(mock_tempfile)
    expected_config = {
        "page": {
            "headers": {
                "Cookie": "nocookieforyou",
            }
        }
    }
    assert pa11y_config == expected_config
    mock_remove.assert_called_with("mockconfig.json")


def test_pa11y_not_installed(mocker):
    mock_check_call = mocker.patch(
        "subprocess.check_call", side_effect=OSError
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
        "page_title": "Sparkly Ponies of Joy",
        "request_headers": {"Cookie": "nocookieforyou"},
        "accessed_at": datetime(2016, 8, 20, 14, 12, 45),
    }
    fake_pa11y_data = {
        "results": [{
            "message": "Check that the title element describes the document.",
            "code": "WCAG2AA.Principle2.Guideline2_4.2_4_2.H25.2",
            "type": "notice",
            "html": "<title>Evil Demons of Despa...</title>"
        }]
    }

    # setup
    data_dir = tmpdir.mkdir("data")
    spider = mocker.Mock(data_dir=str(data_dir))

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
        'Parser mismatch! Scrapy saw full title "Sparkly Ponies of Joy", '
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
    fake_pa11y_data = {
        "count": {
            "error": 2,
            "warning": 5,
            "notice": 10,
            "total": 17,
        }
    }

    # setup
    data_dir = tmpdir.mkdir("data")
    spider = mocker.Mock(data_dir=str(data_dir))

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
    inc_value.assert_any_call("pa11y/error", count=2, spider=spider)
    inc_value.assert_any_call("pa11y/warning", count=5, spider=spider)
    inc_value.assert_any_call("pa11y/notice", count=10, spider=spider)
