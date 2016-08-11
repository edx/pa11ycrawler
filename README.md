Overview
========

pa11ycrawler a [Scrapy](http://doc.scrapy.org/en/latest/index.html)
spider that calls [Pa11y](http://pa11y.org/) on every page of a locally-running
Open edX installation, to audit it for accessibility purposes.
It will store the result of each page audit in a data directory as a set of
JSON files, which can be transformed into a beautiful HTML report.

Installation
============

pa11ycrawler requires Python 2.7 and Node.js installed.

```
pip install .
npm install
```

Usage
=====

```
scrapy crawl edx
```

There are several options for this spider that you can configure using the
`-a` scrapy flag.

Option       | Default                        | Example
------------ | ------------------------------ | -------
`domain`     | `localhost`                    | `scrapy crawl edx -a domain=edx.org`
`port`       | `8000`                         | `scrapy crawl edx -a port=8003`
`course_key` | `course-v1:edX+Test101+course` | `scrapy crawl edx -a course_key=org/course/run`
`data_dir`   | `data`                         | `scrapy crawl edx -a data_dir=~/pa11y-data`

These options can be combined by specifying the `-a` flag multiple times.
For example, `scrapy crawl edx -a domain=courses.edx.org -a port=80`.

The `data_dir` option is used to determine where this crawler will save its
output. pa11ycrawler will run each page of the site through `pa11y`,
encode the result as JSON, and save it as a file in this directory.
This data directory is "data" by default, which means it will create a directory
named "data" in whatever directory you run the crawler from.
Whatever directory you specify, it will be automatically created if it does
not yet exist. In addition, this tool will never delete data from the data
directory, so if you want to clear it out between runs, that's your
responsibility!

Transform to HTML
=================

This project comes with a script that can transform the data in this
data directory into a pretty HTML table. The script is installed as
`pa11ycrawler-html` and it accepts two optional arguments: `--data-dir`
and `--output-dir`. These arguments default to "data" and "html",
respectively.

You can also run the script with the `--help` argument to get more information.

Running Tests
=============

This project has tests for the pipeline functions, where are where the main
functionality of this crawler lives. To run those tests, run `py.test` or
`make test`. You can also run `scrapy check edx` to test that the
scraper is scraping data correctly.
