"""Tests for html.py methods. """
from datetime import datetime
import os
from path import Path

import pytest

from pa11ycrawler.html import render_html
from pa11ycrawler.pipelines.pa11y import write_pa11y_results


@pytest.fixture(params=["Snowman", u"\u2603"])
def item(request):
    return {
        "url": "http://courses.edx.org/fakepage",
        "page_title": request.param,
        "request_headers": {"Cookie": "nocookieforyou"},
        "accessed_at": datetime(2016, 8, 20, 14, 12, 45),
    }


def test_render_html(item, tmpdir_factory):
    tmp_data_dir = Path(tmpdir_factory.mktemp('data'))
    pa11y_data = [{
        "message": "Check that the title element describes the document.",
        "code": "WCAG2AA.Principle2.Guideline2_4.2_4_2.H25.2",
        "type": "notice",
        "context": "<title>\t\nThis is a Fake Pa...</title>",
        "selector": "#fake > div",
    }]
    write_pa11y_results(item, pa11y_data, tmp_data_dir)
    render_html(tmp_data_dir, tmp_data_dir)
    assert os.path.isfile(os.path.join(tmp_data_dir, 'index.html'))
