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
from lxml import html

from scrapy.exceptions import DropItem, NotConfigured
from pa11ycrawler.util import DateTimeEncoder

DEVNULL = open(os.devnull, 'wb')


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

    def __init__(self):
        "Check to be sure that `pa11y` is installed properly"
        try:
            sp.check_call(
                [self.pa11y_path, "--version"],
                stdout=DEVNULL, stderr=DEVNULL,
            )
        except OSError:
            # No such file or directory
            msg = (
                "pa11y is not installed at {path}. "
                "Run `npm install` to install it."
            ).format(path=self.pa11y_path)
            raise NotConfigured(msg)

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

    def check_title_match(self, expected_title, pa11y_output, logger):
        """
        Check if Scrapy reports any issue with the HTML <title> element.
        If so, compare that <title> element to the title that we got in the
        A11yItem. If they don't match, something is screwy, and pa11y isn't
        parsing the page that we expect.
        """
        if not pa11y_output:
            # no output from pa11y, nothing to check.
            return
        pa11y_results = json.loads(pa11y_output).get("results")
        if not pa11y_results:
            return
        title_errs = [err for err in pa11y_results
                      if err["html"].startswith("<title")]
        for err in title_errs:
            title_elmt = html.fragment_fromstring(err["html"])
            # pa11ycrawler will elide the title, so grab whatever true
            # content we can from the output
            elided_title = title_elmt.text.strip()
            if elided_title.endswith("..."):
                pa11y_title = elided_title[0:-3]
            else:
                pa11y_title = elided_title

            # check that they match -- the elided version should be a substring
            # of the full version
            if pa11y_title not in expected_title:
                # whoa, something's screwy!
                msg = (
                    'Parser mismatch! '
                    'Scrapy saw full title "{scrapy_title}", '
                    'Pa11y saw elided title "{elided_title}".'
                ).format(
                    scrapy_title=expected_title, elided_title=elided_title,
                )
                logger.error(msg)

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

        self.check_title_match(item['page_title'], stdout, spider.logger)
        os.remove(config_file.name)
        self.write_pa11y_results(item, stdout, spider.data_dir)
        return item
