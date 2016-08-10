import pytest
import json
from datetime import datetime
from StringIO import StringIO
import subprocess as sp
from scrapy.exceptions import DropItem
from pa11ycrawler.pipelines import (
    DuplicatesPipeline, DropDRFPipeline, Pa11yPipeline
)


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
    pa11y_pl = Pa11yPipeline()
    # setup
    data_dir = tmpdir.mkdir("data")
    spider = mocker.Mock(data_dir=str(data_dir))
    mock_process = mocker.Mock(returncode=None)
    fake_pa11y_data = {"pa11y": "output"}
    def mock_communicate():
        mock_process.returncode = 2
        # returns both stdout and stderr
        return json.dumps(fake_pa11y_data), ""
    mock_process.communicate.side_effect = mock_communicate
    mock_Popen = mocker.patch("subprocess.Popen", return_value=mock_process)
    mock_tempfile = StringIO()
    mock_tempfile.name = "mockconfig.json"
    mock_tempfile_ctor = mocker.patch(
        "tempfile.NamedTemporaryFile",
        return_value=mock_tempfile,
    )
    mock_remove = mocker.patch("os.remove")
    item = {
        "url": "http://courses.edx.org/fakepage",
        "page_title": "This is a Fake Page",
        "request_headers": {"Cookie": ["nocookieforyou"]},
        "accessed_at": datetime(2016, 8, 20, 14, 12, 45),
    }

    # test
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

    # one data file should be output correctly
    data_files = data_dir.listdir()
    assert len(data_files) == 1
    data_file = data_files[0]
    assert data_file.basename == 'c13d12d109449354e331b1b2f062dcb6.json'
    data_from_file = json.load(data_file)
    fake_pa11y_data.update(item)
    fake_pa11y_data["accessed_at"] = fake_pa11y_data["accessed_at"].isoformat()
    assert data_from_file == fake_pa11y_data

