# -*- coding: utf-8 -*-
"""
Item pipelines. Pipelines are enabled via the ITEM_PIPELINES setting.
See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
"""
from urlobject import URLObject
from scrapy.exceptions import DropItem

from .pa11y import Pa11yPipeline


class DuplicatesPipeline(object):
    """
    Ensures that we only process each URL once. Assume that if two URLs
    differ only by their querystring, they should be treated as the same
    URL, and only one should be processed.
    """
    def __init__(self):
        self.urls_seen = set()

    def clean_url(self, url):
        """
        Remove querystrings.
        """
        return URLObject(url).without_query()

    def process_item(self, item, spider):  # pylint: disable=unused-argument
        """
        Stops processing item if we've already seen this URL before.
        """
        url = self.clean_url(item["url"])
        if url in self.urls_seen:
            raise DropItem("Dropping duplicate url {url}".format(url=item["url"]))
        else:
            self.urls_seen.add(url)
            return item


class DropDRFPipeline(object):
    """
    Drop pages that are generated from Django Rest Framework (DRF), so that
    they don't get processed by pa11y later in the pipeline.
    """
    def process_item(self, item, spider):  # pylint: disable=unused-argument
        "Check for DRF urls."
        url = URLObject(item["url"])
        if url.path.startswith("/api/"):
            raise DropItem("Dropping DRF url {url}".format(url=url))
        else:
            return item
