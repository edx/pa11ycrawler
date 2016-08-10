# -*- coding: utf-8 -*-
"""
Item pipelines. Pipelines are enabled via the ITEM_PIPELINES setting.
See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
"""
import os
import json
import subprocess as sp
import tempfile
import hashlib
from urlobject import URLObject

from scrapy.exceptions import DropItem
from pa11ycrawler.util import DateTimeEncoder


class DuplicatesPipeline(object):
    """
    Ensures that we only process each URL once.
    """
    def __init__(self):
        self.urls_seen = set()

    def clean_url(self, url):
        """
        A `next` query parameter indicates where the user should be
        redirected to next -- it doesn't change the content of the page.
        Two URLs that only differ by their `next` query paramenter should
        be considered the same.
        """
        return URLObject(url).del_query_param("next")

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


class Pa11yPipeline(object):
    """
    Runs the Pa11y CLI against `item['url']`, using the same request headers
    used by Scrapy.
    """
    pa11y_path = "node_modules/.bin/pa11y"
    cli_flags = {
        "reporter": "1.0-json",
    }

    def write_pa11y_config(self, item):
        """
        The only way that pa11y will see the same page that scrapy sees
        is to make sure that pa11y requests the page with the same headers.
        However, the only way to configure request headers with pa11y is to
        write them into a config file.

        This function will create a config file, write the config into it,
        and return a reference to that file.
        """
        config = {
            "page": {
                "headers": item["request_headers"],
            },
        }
        config_file = tempfile.NamedTemporaryFile(
            mode="w",
            prefix="pa11y-config-",
            suffix=".json",
            delete=False
        )
        json.dump(config, config_file)
        config_file.close()
        return config_file

    def write_pa11y_results(self, item, results, data_dir):
        """
        Write the output from pa11y into a data file.
        """
        # `pa11y` outputs JSON, so we'll just add a bit more info for context
        data = json.loads(results)
        data.update(item)

        # it would be nice to use the URL as the filename,
        # but that gets complicated (long URLs, special characters, etc)
        # so we'll make the filename a hash of the URL instead,
        # and throw in the access time so that we can store the same URL
        # multiple times in this data directory
        hasher = hashlib.md5()
        hasher.update(item["url"])
        hasher.update(item["accessed_at"].isoformat())
        basename = hasher.hexdigest()
        filename = basename + ".json"
        filepath = os.path.join(data_dir, filename)

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        with open(filepath, 'w') as f:
            json.dump(data, f, cls=DateTimeEncoder)

    def process_item(self, item, spider):
        """
        Use the Pa11y command line tool to get an a11y report.
        """
        config_file = self.write_pa11y_config(item)
        args = [
            self.pa11y_path,
            item["url"],
            '--config={file}'.format(file=config_file.name),
        ]
        for flag, value in self.cli_flags.items():
            args.append("--{flag}={value}".format(flag=flag, value=value))

        retries_remaining = 3
        while retries_remaining:
            logline = " ".join(args)
            if retries_remaining != 3:
                logline += "  # (retry {num})".format(num=3-retries_remaining)
            spider.logger.info(logline)

            proc = sp.Popen(
                args, shell=False,
                stdout=sp.PIPE, stderr=sp.PIPE,
            )
            stdout, stderr = proc.communicate()
            if proc.returncode in (0, 2):
                # `pa11y` ran successfully!
                # Return code 0 means no a11y errors.
                # Return code 2 means `pa11y` identified a11y errors.
                # Either way, we're done, so break out of the `while` loop
                break
            else:
                # `pa11y` did _not_ run successfully!
                # We sometimes get the error "Truffler timed out":
                # truffler is what accesses the web page for `pa11y1`.
                # https://www.npmjs.com/package/truffler
                # If this is the error, we can resolve it just by trying again,
                # so decrement the retries_remaining and start over.
                retries_remaining -= 1

        if retries_remaining == 0:
            raise DropItem(
                "Couldn't get pa11y results for {url}. Error:\n{err}".format(
                    url=item['url'],
                    err=stderr,
                )
            )

        os.remove(config_file.name)
        self.write_pa11y_results(item, stdout, spider.data_dir)
        return item
