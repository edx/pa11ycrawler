Overview
========

pa11ycrawler is a python command line tool built using [Scrapy](http://doc.scrapy.org/en/latest/index.html) and [Pa11y](http://pa11y.org/) for
crawling a website and storing a Pa11y report for each page.

The reports can be in the form of any of Pa11y's default report types or [1.0-json](https://github.com/springernature/pa11y-reporter-1.0-json).  There is an additional command to produce html reports from the 1.0-json.

Installation
============

Prereqs
-------

* python (v2.7)
* node.js

Install node Requirements
-------------------------
```
npm install -g pa11y@3.6.0 pa11y-reporter-1.0-json@1.0.2
```

Install via GitHub
------------------
```
pip install git+https://github.com/edx/pa11ycrawler.git
```

Install via PyPi
----------------
TODO


Usage
=====

Basic usage
-----------
For help:

```
pa11ycrawler -h
```

Running the crawler
-------------------

To run the crawler, producing json reports
```
pa11ycrawler run $START_URL --pa11ycrawler-allowed-domains=$ALLOWED_DOMAINS --pa11y-reporter='1.0-json'
```

NOTE: You probably want to make sure that `--pa11ycrawler-allowed-domains` is set, or you may start crawling external sites.

For more options:
```
pa11ycrawler run -h
```


Produce html reports from the 1.0-json reports
----------------------------------------------


To run the crawler, producing json reports
```
pa11ycrawler json-to-html
```

For more options:
```
pa11ycrawler json-to-html -h
```


Development
===========

Prereqs
-------

* python (v2.7)
* node.js
* make

Get the code
------------
```
git clone https://github.com/edx/pa11ycrawler.git
```

Install python and node requirements
------------------------------------
```
make develop
```

Running unit tests
-------------
```
make test
```

Checking code quality (pep8 and pylint)
---------------------------------------
```
make quality
```
