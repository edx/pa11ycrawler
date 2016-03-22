# -*- coding: utf-8 -*-
"""
Item pipelines. Pipelines are enabled via the ITEM_PIPELINES setting.
See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
"""
import os
import json
import subprocess
import tempfile

from scrapy.exceptions import DropItem

from pa11ycrawler.settings_helpers import is_pa11y_setting


class DuplicatesPipeline(object):
    """
    Ensures that we only process each URL once.
    """
    def __init__(self):
        self.urls_seen = set()

    def process_item(self, item, _spider):
        """
        Stops processing item if we've already seen this URL before.
        """
        if item['url'] in self.urls_seen:
            raise DropItem("[Skipping] Duplicate url found: {}".format(item['url']))
        else:
            self.urls_seen.add(item['url'])
            return item


class Pa11yPipeline(object):
    """
    Runs the Pa11y CLI against `item['url']`, using the same headers used by
    Scrapy. Stores the results in `item['results']` to be processed by
    `spider.a11y_reporter`.
    """
    def __init__(self):
        self.pa11y_settings = None

    def get_pa11y_settings(self, spider):
        """
        Sets `self.pa11y_settings` to the list of flags that should
        be passed to the Pa11y CLI.
        """
        settings = []
        for key, value in spider.settings.attributes.iteritems():
            if is_pa11y_setting(key) and value.value:
                flag_name = key.replace('_', '-').split('PA11Y-')[1].lower()
                flag = '--{}="{}"'.format(flag_name, value.value)
                settings.append(flag)

        self.pa11y_settings = settings
        return settings

    def _gen_pa11y_config(self, headers):
        """
        Creates tempfile with pa11y configuration.
        This includes any headers that need to be kept.
        Returns the file path of the new file.
        """
        config = json.dumps({
            "page": {
                "headers": headers,
            },
        })

        pa11y_config_fp = tempfile.mkstemp(suffix='.json')[1]
        with open(pa11y_config_fp, 'w') as pa11y_config_file:
            pa11y_config_file.write(config)

        return pa11y_config_fp

    def process_item(self, item, spider):
        """
        Use the Pa11y command line tool to get an a11y report.
        """
        pa11y_config_file = self._gen_pa11y_config(item["headers"])
        base_command = [
            'pa11y',
            '"{}"'.format(item['url']),
            '--config="{}"'.format(pa11y_config_file),
        ]
        pa11y_settings = self.pa11y_settings or self.get_pa11y_settings(spider)
        command = ' '.join(base_command + pa11y_settings)
        spider.logger.info("RUNNING PA11Y: %s", command)

        try:
            item['results'] = subprocess.check_output(command, shell=True)

        except subprocess.CalledProcessError, err:
            if err.returncode == 2:
                # When accessibility errors are found, but the process
                # completes successfully, exit code 2 is returned
                item['results'] = err.output
            else:
                raise DropItem(
                    "Couldn't get pa11y results for {}. Error:\n{}".format(
                        item['url'],
                        err.output
                    )
                )

        os.remove(pa11y_config_file)
        spider.a11y_reporter.add_results(item)
        return item
