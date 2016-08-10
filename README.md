Overview
========

pa11ycrawler a [Scrapy](http://doc.scrapy.org/en/latest/index.html)
spider that calls [Pa11y](http://pa11y.org/) on every page of a locally-running
Open edX installation, to audit it for accessibiltiy purposes.
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

Make sure you have an Open edX instance running at `localhost:8003`, then run:

```
scrapy crawl local-edx
```

By default, pa11ycrawler will crawl through the edX101 demo course (course
key `course-v1:edX+Test101+course`), but you can specify whatever course key
you'd like with the `-a` flag, like this:

```
scrapy crawl local-edx -a course_key=org/course/run
```

pa11ycrawler will run each page through `pa11y`, encode the result as JSON,
and save it as a file in a data directory. This data directory is "data" by
default (as in, a directory named "data" that is at the same location that
you run the `scrapy crawl` command from), but you can also change this with
the `-a` flag, like this:

```
scrapy crawl local-edx -a data_dir=~/pa11y-data
```

Whatever directory you specify, it will be automatically created if it does
not yet exist. In addition, this tool will never delete data from the data
directory, so if you want to clear it out between runs, that's your
responsibility!

Transform to HTML
=================

This project comes with a script that can transform the data in this
data directory into a pretty HTML table. The script is called
`gen_html.py`, and it accepts two optional arguments: `--data-dir`
and `--output-dir`. These arguments default to "data" and "html",
respectively.

You can also run the script with the `--help` argument to get more information.

Running Tests
=============

This project has tests for the pipeline functions, where are where the main
functionality of this crawler lives. To run those tests, run `py.test` or
`make test`. You can also run `scrapy check local-edx` to test that the
scraper is scraping data correctly.
