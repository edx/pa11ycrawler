# -*- coding: utf-8 -*-
"""
This module defines the ways in which the data obtained from the
Pa11ySpider and Pa11yPipleline is processed.
"""
import json
import logging
import os
import re
import shutil

from abc import ABCMeta, abstractmethod
from collections import defaultdict, Counter
from mako.lookup import TemplateLookup

log = logging.getLogger(__name__)


def get_code_info(code):
    """
    Method for getting links to docs to present in reports.

    Args: code (example: WCAG2AA.Principle3.Guideline3_2.3_2_1.G107)
    Returns: a dict mapping technique to documentation url.
    """
    link_info = {'doc_links': {}, 'base_code': ''}
    base_url = 'https://www.w3.org/TR/WCAG20-TECHS/'

    guide_pattern = re.compile(r'WCAG2AA.Principle\d.Guideline[0-9\_\.]*')
    base_code_matches = guide_pattern.match(code)

    if not base_code_matches:
        log.debug(
            'Code {code} doesn\'t match expected pattern. Unable to produce '
            'documentation links for reports.'.format(code=code)
        )
        return link_info

    link_info['base_code'] = base_code_matches.group()[0:-1]
    split_code = guide_pattern.split(code)
    tech_group = split_code[1]
    tech_pattern = re.compile(r'[A-Z]+\d{1,3}')
    techs = tech_pattern.findall(tech_group)

    for tech in techs:
        link_info['doc_links'][tech] = base_url + tech

    return link_info


class ReporterBaseClass(object):
    """
    Defines reporting directory structure and settings.
    """
    def __init__(self, settings):
        self.settings = settings
        self.reports_dir = settings.get('PA11YCRAWLER_REPORTS_DIR')
        self.keep_existing = settings.get(
            'PA11YCRAWLER_KEEP_EXISTING_REPORTS')

        self.source_dir = os.path.join(self.reports_dir, 'source')
        self.results_dir = os.path.join(self.reports_dir, 'results')
        self.html_dir = os.path.join(self.reports_dir, 'html')
        self.results_map_file = os.path.join(self.results_dir, 'pa11y-summary.json')
        self.results_map = {}


class Pa11yAbstractSpiderReporter():
    """
    Defines the expected methods. These are the points during a crawl when
    the reported will be accessed.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def add_results(self, item):
        """
        Called for every `A11yItem` processed through `Pa11yPipeline`.
        """
        raise NotImplementedError

    @abstractmethod
    def pre_process_reports(self):
        """
        Called before Pa11ySpider starts crawling.
        Use for setting up and cleaning report directories, etc.
        """
        raise NotImplementedError

    @abstractmethod
    def post_process_reports(self):
        """
        Called when Pa11ySpider has finished crawling.
        All items that will be processed will be done at this point.
        Use for aggregating stats accross pages, etc.
        """
        raise NotImplementedError


class Pa11yGenericReporter(ReporterBaseClass, Pa11yAbstractSpiderReporter):
    """
    Defines the default way of processing the Pa11y results.
    """
    def _save_html(self, item):
        """
        Saves the source html to `self.html_dir` if `PA11YCRAWLER_SAVE_SOURCE`
         is `True`.
        """
        if self.settings.get('PA11YCRAWLER_SAVE_SOURCE'):
            if not os.path.exists(self.source_dir):
                os.makedirs(self.source_dir)

            filepath = os.path.join(
                self.source_dir, item['filename'] + '.html')

            with open(filepath, 'w') as html_file:
                html_file.write(item['source'])

    def _update_results_map(self, item):
        """
        Adds these results to `self.results_map`.
        See documentation of `A11yItem` for details about the filename.
        """
        self.results_map[item['url']] = {
            'filename': item['filename'],
            'page_title': item['page_title'],
        }

    def add_results(self, item):
        """
        Saves file to `self.results_dir`.
        """
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

        filename = '{}.{}'.format(
            item['filename'],
            self.settings.get('PA11Y_REPORTER').replace('-', '.')
        )

        filepath = os.path.join(self.results_dir, filename)
        with open(filepath, 'w') as report:
            report.write(item['results'])

        self._update_results_map(item)
        self._save_html(item)

    def pre_process_reports(self):
        """
        Sets up directories for reports.
        """
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)
        elif not self.settings.get('PA11YCRAWLER_KEEP_EXISTING_REPORTS'):
            shutil.rmtree(self.reports_dir)

    def post_process_reports(self):
        """
        Saves the `results_map`, which maps a url to the basename of the file
        that contains its results.
        """
        results_map_file = os.path.join(
            self.reports_dir, 'results', 'pa11y-summary.json')

        with open(results_map_file, 'w') as results_map:
            json.dump(self.results_map, results_map)


class HtmlReporter(ReporterBaseClass):
    """
    Generates html reports for the results from Pa11yJsonReporter.
    """
    def __init__(self, settings, *args, **kwargs):
        super(HtmlReporter, self).__init__(settings, *args, **kwargs)

        # where templates are
        par_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(par_dir, 'templates')
        self.template_lookup = TemplateLookup(directories=[self.templates_dir])
        self.color_classes = {
            'error': 'danger',
            'warning': 'warning',
            'notice': 'info',
        }
        self.summary = {
            "pageResults": {},
            "overallCount": {
                "total": 0,
                "error": 0,
                "warning": 0,
                "notice": 0,
                "pages_affected": 0,
            }
        }
        self.summary_by_code = defaultdict(dict)

    def make_html(self):
        """
        Main method of this class. Generates HTML reports from the
        JSON files found in `self.results_dir`.
        """
        self._setup_dir()
        self._copy_assets()

        with open(self.results_map_file, 'r') as report:
            self.results_map = json.load(report)

        for url, info in self.results_map.iteritems():
            result_file = os.path.join(self.results_dir, info['filename'] + '.1.0.json')

            with open(result_file, 'r') as report:
                try:
                    results = json.load(report)
                except ValueError as error:
                    log.error(error.message)
                    continue

            self._make_page_result_html(url, info, results)
            self._update_summary(url, info, results)

        self._make_summary_by_code_html()
        self._make_index_html()

    def _update_summary(self, url, info, results):
        """
        Updates `self.summary` to include the total, error, warning, and
        notice counts from this URL's results.
        """
        self.summary["pageResults"][url] = results["count"]
        self.summary["pageResults"][url].update(info)
        self.summary["overallCount"]["total"] += results["count"]["total"]
        self.summary["overallCount"]["error"] += results["count"]["error"]
        self.summary["overallCount"]["warning"] += results["count"]["warning"]
        self.summary["overallCount"]["notice"] += results["count"]["notice"]
        self.summary["overallCount"]["pages_affected"] += 1

        for result in results['results']:
            self.summary_by_code[result['code']]['type'] = result['type']
            self.summary_by_code[result['code']]['message'] = result['message']

            if not self.summary_by_code[result['code']].get('pages'):
                self.summary_by_code[result['code']]['pages'] = set()

            self.summary_by_code[result['code']]['pages'].add((
                info['page_title'].strip() if info['page_title'] else '', url
            ))

    def _setup_dir(self):
        """
        Sets up `self.html_dir` for new reports.
        * Makes sure the directory exists
        * Removes existing reports, unless `self.keep_existing` is true.
        """
        if not os.path.exists(self.html_dir):
            os.makedirs(self.html_dir)
        elif not self.keep_existing:
            shutil.rmtree(self.html_dir)

    def _copy_assets(self):
        """
        Copy any needed assets to the report directory.
        """
        template_assets_dir = os.path.join(
            self.templates_dir,
            'assets'
        )

        results_assets_dir = os.path.join(
            self.html_dir,
            'assets'
        )
        try:
            shutil.copytree(template_assets_dir, results_assets_dir)
        except (shutil.Error, OSError) as err:
            # If this fails because the directory already exists (for example),
            # we want to keep going. The results just won't have styling/js.
            print 'Directory not copied. {}'.format(err)

    def _make_page_result_html(self, url, info, results):
        """
        Makes an html report for the given URL.
        """
        html_file = os.path.join(self.html_dir, info['filename'] + '.html')
        result_template = self.template_lookup.get_template('result.html')

        log.debug('Making {}'.format(html_file))

        context = {
            'url': url,
            'info': info,
            'get_code_info': get_code_info,
            'report': results,
            'color_classes': self.color_classes,
            'sort_order': {
                'error': '0',
                'warning': '1',
                'notice': '2',
            },
        }
        rendered_html = result_template.render(**context)

        log.info(
            "SUMMARY FOR %s: %s",
            info['page_title'].strip() if info['page_title'] else '',
            json.dumps(results['count'])
        )

        with open(html_file, 'w+') as filepath:
            filepath.write(rendered_html.encode("UTF-8"))

    def _make_summary_by_code_html(self):
        """
        Makes an html file that summarizes the results by mapping the issue
        code to the pages affected by it.
        """
        log.debug('Making summary_by_code.html')

        index_template = self.template_lookup.get_template('summary_by_code.html')

        counts_by_type = Counter([code['type'] for code in self.summary_by_code.values()])
        counts_by_type['total'] = len(self.summary_by_code.keys())

        context = {
            'results': self.summary_by_code,
            'get_code_info': get_code_info,
            'color_classes': self.color_classes,
            'counts_by_type': counts_by_type,
        }

        log.info(
            "PA11YCRAWLER SUMMARY BY ISSUE CODE: %s",
            json.dumps(counts_by_type)
        )

        summary_html = index_template.render(**context)
        filepath = os.path.join(self.html_dir, 'summary_by_code.html')
        with open(filepath, 'w+') as summary_file:
            summary_file.write(summary_html.encode('utf-8'))

    def _make_index_html(self):
        """
        Makes an html file that summarizes the results and links to
        individual page results.
        """
        log.debug('Making index.html')

        index_template = self.template_lookup.get_template('index.html')

        context = {
            'count': self.summary['overallCount'],
            'pageResults': self.summary['pageResults'],
        }

        log.info(
            "PA11YCRAWLER SUMMARY BY ISSUE INSTANCE: %s",
            json.dumps(context['count'])
        )

        index_html = index_template.render(**context)
        filepath = os.path.join(self.html_dir, 'index.html')
        with open(filepath, 'w+') as index_file:
            index_file.write(index_html.encode('utf-8'))
