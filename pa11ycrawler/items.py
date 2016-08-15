# -*- coding: utf-8 -*-
"""
The models for scraped items

See documentation in:
http://doc.scrapy.org/en/latest/topics/items.html
"""
from scrapy.item import Item, Field


class A11yItem(Item):
    """
    The output of scraping each page. These are the only pieces of data we
    care about for a given page.
    """
    url = Field()
    request_headers = Field()
    accessed_at = Field()
    page_title = Field()
