# -*- coding: utf-8 -*-
"""
The models for scraped items

See documentation in:
http://doc.scrapy.org/en/latest/topics/items.html
"""
from scrapy.item import Item, Field


class A11yItem(Item):
    """
    Fields for an item scraped with pa11y:
    * url (url visited)
    * filename (md5 hash of url)
    * headers (passed to pa11y)
    * results (pa11y results)
    * source (source html)
    """
    url = Field()
    page_title = Field()
    filename = Field()
    headers = Field()
    results = Field()
    source = Field()
