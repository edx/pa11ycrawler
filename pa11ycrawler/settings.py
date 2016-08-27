# -*- coding: utf-8 -*-
"""
Scrapy settings for a11y project

For simplicity, this file contains only settings considered important or
commonly used. You can find more settings consulting the documentation:

    http://doc.scrapy.org/en/latest/topics/settings.html
    http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
    http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
"""

# Main settings used by crawler: handle with care! --------
SPIDER_MODULES = ['pa11ycrawler.spiders']
NEWSPIDER_MODULE = 'pa11ycrawler.spiders'
DEFAULT_ITEM_CLASS = 'pa11ycrawler.items.A11yItem'

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'pa11ycrawler.pipelines.DuplicatesPipeline': 200,
    'pa11ycrawler.pipelines.DropDRFPipeline': 250,
    'pa11ycrawler.pipelines.Pa11yPipeline': 300,
}

# Other items you are likely to want to override ---------------
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
COOKIES_DEBUG = False
COOKIES_ENABLED = True
DEPTH_LIMIT = 6
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(name)s]: %(message)s'
