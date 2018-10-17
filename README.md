[![Build Status](https://travis-ci.org/edx/pa11ycrawler.svg?branch=master)](https://travis-ci.org/edx/pa11ycrawler)
[![Coverage Status](https://img.shields.io/codecov/c/github/edx/pa11ycrawler/master.svg)](https://codecov.io/gh/edx/pa11ycrawler)

Pa11ycrawler
============

pa11ycrawler is a [Scrapy](http://doc.scrapy.org/en/latest/index.html)
spider that runs a [Pa11y](http://pa11y.org/) check on every page of an
Open edX installation, to audit it for accessibility purposes.
It will store the result of each page audit in a data directory as a set of
JSON files, which can be transformed into a beautiful HTML report.

Installation
============

pa11ycrawler requires Python 2.7+ and Node.js 8+ installed.  You must also
install Google Chrome, which the
[Puppeteer](https://developers.google.com/web/tools/puppeteer/) library used
by pa11ycralwer uses to run accessibility tests on each page of a website.
You also need to set the following environment variables before installing NPM
dependencies:

* PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=1
* PUPPETEER_EXECUTABLE_PATH={path to Google Chrome binary}

If these are not set, Puppeteer will download a separate copy of Chromium
(but none of its dependencies, leaving it unusable in most Docker containers
and headless servers).

```
make install
```

Usage
=====

```
scrapy crawl edx
```

There are several options for this spider that you can configure using the
`-a` scrapy flag.

Option                    | Default                        | Example
------------------------- | ------------------------------ | -------
`domain`                  | `localhost`                    | `scrapy crawl edx -a domain=edx.org`
`port`                    | `8000`                         | `scrapy crawl edx -a port=8003`
`email`                   | None                           | `scrapy crawl edx -a email=staff@example.com -a password=edx`
`password`                | None                           | (see above)
`http_user`               | None                           | `scrapy crawl edx -a http_user=grace -a http_pass=hopper`
`http_pass`               | None                           | (see above)
`course_key`              | `course-v1:edX+Test101+course` | `scrapy crawl edx -a course_key=org/course/run`
`pa11y_ignore_rules_file` | None                           | `scrapy crawl edx -a pa11y_ignore_rules_file=/tmp/ignore.yaml`
`pa11y_ignore_rules_url`  | None                           | `scrapy crawl edx -a pa11y_ignore_rules_url=https://...`
`data_dir`                | `data`                         | `scrapy crawl edx -a data_dir=~/pa11y-data`
`single_url`			  | None						   | `scrapy crawl edx -a single-url=http://localhost:8003/courses/`

These options can be combined by specifying the `-a` flag multiple times.
For example, `scrapy crawl edx -a domain=courses.edx.org -a port=80`.

If an email and password are not specified, then pa11ycrawler will use the
"auto auth" feature in Open edX to create a staff user, and crawl as that user.
Note that this assumes that the "auto auth" feature is enabled -- if not, the
crawler won't be able to crawl without an email and password set.

The `http_user` and `http_pass` arguments are used for HTTP Basic Auth. If
either of these is unset, pa11ycrawler will not attempt to use HTTP Basic auth.

The `pa11y_ignore_rules_file` and `pa11y_ignore_rules_url` arguments
allow you to specify a YAML file, or the URL to a YAML file, containing
pa11y ignore rules. These rules are used to indicate that certain
output from pa11y has been manually checked, and can be safely ignored.

The `data_dir` option is used to determine where this crawler will save its
output. pa11ycrawler will run each page of the site through `pa11y`,
encode the result as JSON, and save it as a file in this directory.
This data directory is "data" by default, which means it will create a directory
named "data" in whatever directory you run the crawler from.
Whatever directory you specify, it will be automatically created if it does
not yet exist. The crawler will never delete data from the data directory,
so if you want to clear it out between runs, that's your responsibility.
There is a `make clean-data` task available in the Makefile, which just runs
`rm -rf data`.

The `single_url` option is available to allow the spider to only crawl one web page. 
The result is evaluated through the pipeline, but the spider will not continue crawling
afterwards.

Transform to HTML
=================

This project comes with a script that can transform the data in this
data directory into a pretty HTML table. The script is installed as
`pa11ycrawler-html` and it accepts two optional arguments: `--data-dir`
and `--output-dir`. These arguments default to "data"
and "html", respectively.

You can also run the script with the `--help` argument to get more information.

Cleaning Data & HTML
====================

This project comes with a `Makefile` with a `clean-data` task and a `clean-html`
task. The former will delete the `data` directory in the current working
directory, and the latter will delete the `html` directory in the current
working directory. These are the default locations for pa11ycrawler's data and
HTML. However, if you configure pa11ycrawler to output data and/or HTML
to a different location, this task has no way of knowing where
the data and HTML are located on your computer,
and will not be able to automatically remove them for you.

To remove data from the default location, run:
```
make clean-data
```
To remove HTML from the default location, run:
```
make clean-html
```

Running Tests
=============

This project has tests for the pipeline functions, where the main
functionality of this crawler lives. To run those tests, run `py.test` or
`make test`. You can also run `scrapy check edx` to test that the
scraper is scraping data correctly.
