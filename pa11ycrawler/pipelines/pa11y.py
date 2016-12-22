# -*- coding: utf-8 -*-
"""
Contains the Pa11yPipeline, and all supporting functions.
"""
import os
import json
import fnmatch
import subprocess as sp
import tempfile
import hashlib
import itertools
from lxml import html
from path import Path

from scrapy.exceptions import DropItem, NotConfigured
from pa11ycrawler.util import DateTimeEncoder, pa11y_counts

DEVNULL = open(os.devnull, 'wb')


def ignore_rules_for_url(spider, url):
    """
    Returns a list of ignore rules from the given spider,
    that are relevant to the given URL.
    """
    ignore_rules = getattr(spider, "pa11y_ignore_rules", {}) or {}
    return itertools.chain.from_iterable(
        rule_list
        for url_glob, rule_list
        in ignore_rules.items()
        if fnmatch.fnmatch(url, url_glob)
    )


def ignore_rule_matches_result(ignore_rule, pa11y_result):
    """
    Returns a boolean result of whether the given ignore rule matches
    the given pa11y result. The rule only matches the result if *all*
    attributes of the rule match.
    """
    return all(
        fnmatch.fnmatch(pa11y_result.get(attr), ignore_rule.get(attr))
        for attr in ignore_rule.keys()
    )


def load_pa11y_results(stdout, spider, url):
    """
    Load output from pa11y, filtering out the ignored messages.
    The `stdout` parameter is a bytestring, not a unicode string.
    """
    if not stdout:
        return []

    results = json.loads(stdout.decode('utf8'))

    ignore_rules = ignore_rules_for_url(spider, url)
    for rule in ignore_rules:
        results = [
            result for result in results
            if not ignore_rule_matches_result(rule, result)
        ]
    return results


def write_pa11y_config(item):
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


def check_title_match(expected_title, pa11y_results, logger):
    """
    Check if Scrapy reports any issue with the HTML <title> element.
    If so, compare that <title> element to the title that we got in the
    A11yItem. If they don't match, something is screwy, and pa11y isn't
    parsing the page that we expect.
    """
    if not pa11y_results:
        # no output from pa11y, nothing to check.
        return
    title_errs = [err for err in pa11y_results
                  if err["context"].startswith("<title")]
    for err in title_errs:
        title_elmt = html.fragment_fromstring(err["context"])
        # pa11ycrawler will elide the title, so grab whatever true
        # content we can from the output
        elided_title = title_elmt.text.strip()
        if elided_title.endswith("..."):
            pa11y_title = elided_title[0:-4]
        else:
            pa11y_title = elided_title

        # check that they match -- the elided version should be a substring
        # of the full version
        if pa11y_title not in expected_title:
            # whoa, something's screwy!
            msg = (
                u'Parser mismatch! '
                'Scrapy saw full title "{scrapy_title}", '
                'Pa11y saw elided title "{elided_title}".'
            ).format(
                scrapy_title=expected_title, elided_title=elided_title,
            )
            logger.error(msg)


def track_pa11y_stats(pa11y_results, spider):
    """
    Keep track of the number of pa11y errors, warnings, and notices that
    we've seen so far, using the Scrapy stats collector:
    http://doc.scrapy.org/en/1.1/topics/stats.html
    """
    num_err, num_warn, num_notice = pa11y_counts(pa11y_results)
    stats = spider.crawler.stats
    stats.inc_value("pa11y/error", count=num_err, spider=spider)
    stats.inc_value("pa11y/warning", count=num_warn, spider=spider)
    stats.inc_value("pa11y/notice", count=num_notice, spider=spider)


def write_pa11y_results(item, pa11y_results, data_dir):
    """
    Write the output from pa11y into a data file.
    """
    data = dict(item)
    data['pa11y'] = pa11y_results

    # it would be nice to use the URL as the filename,
    # but that gets complicated (long URLs, special characters, etc)
    # so we'll make the filename a hash of the URL instead,
    # and throw in the access time so that we can store the same URL
    # multiple times in this data directory
    hasher = hashlib.md5()
    hasher.update(item["url"].encode('utf8'))
    hasher.update(item["accessed_at"].isoformat().encode('utf8'))
    basename = hasher.hexdigest()
    filename = basename + ".json"
    filepath = data_dir / filename
    data_dir.makedirs_p()
    text = json.dumps(data, cls=DateTimeEncoder)
    filepath.write_text(text)


class Pa11yPipeline(object):
    """
    Runs the Pa11y CLI against `item['url']`, using the same request headers
    used by Scrapy.
    """
    pa11y_path = "node_modules/.bin/pa11y"
    cli_flags = {
        "reporter": "json-oldnode",
    }

    def __init__(self):
        """
        Check to be sure that `pa11y` and `phantomjs` are installed properly.
        """
        try:
            sp.check_call(
                ["phantomjs", "--version"],
                stdout=DEVNULL, stderr=DEVNULL,
            )
        except OSError:
            # No such file or directory
            msg = (
                "phantomjs is not installed, and pa11y cannot run without it. "
                "Install phantomjs through your system package manager."
            )
            raise NotConfigured(msg)
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

    def process_item(self, item, spider):
        """
        Use the Pa11y command line tool to get an a11y report.
        """
        config_file = write_pa11y_config(item)
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

        pa11y_results = load_pa11y_results(stdout, spider, item['url'])
        check_title_match(item['page_title'], pa11y_results, spider.logger)
        track_pa11y_stats(pa11y_results, spider)
        os.remove(config_file.name)
        write_pa11y_results(item, pa11y_results, Path(spider.data_dir))
        return item
