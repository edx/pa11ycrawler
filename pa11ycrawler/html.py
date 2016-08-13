"""
This script transforms JSON from the pa11ycrawler into a beautiful HTML
report.
"""
import os
import os.path
import re
import argparse
import shutil
import json
import logging
import collections
from mako.lookup import TemplateLookup

log = logging.getLogger(__name__)


def make_parser():
    """
    Returns an argparse instance for this script.
    """
    parser = argparse.ArgumentParser(description="generate HTML from crawler JSON")
    parser.add_argument(
        "--data-dir", default="/var/opt/pa11ycrawler/data",
        help="Directory containing JSON data from crawler [%(default)s]"
    )
    parser.add_argument(
        "--output-dir", default="/var/opt/pa11ycrawler/html",
        help="Directory to output the resulting HTML files [%(default)s]"
    )
    return parser


def main():
    """
    Validates script arguments and calls the render_html() function with them.
    """
    parser = make_parser()
    args = parser.parse_args()
    data_dir = os.path.expanduser(args.data_dir)
    if not os.path.exists(data_dir):
        msg = "Data directory {dir} does not exist".format(dir=args.data_dir)
        raise ValueError(msg)
    data_filenames = [name for name in os.listdir(data_dir)
                      if name.endswith(".json")]
    if not data_filenames:
        msg = "Data directory {dir} contains no JSON files".format(dir=args.data_dir)
        raise ValueError(msg)
    output_dir = os.path.expanduser(args.output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    return render_html(data_dir, output_dir)


COLOR_CLASSES = {
    'error': 'danger',
    'warning': 'warning',
    'notice': 'info',
}


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


def render_html(data_dir, output_dir):
    """
    The main workhorse of this script. Finds all the JSON data files
    from pa11ycrawler, and transforms them into HTML files via Mako templating.
    """
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(parent_dir, 'templates')
    template_lookup = TemplateLookup(directories=[templates_dir])
    pages = []
    counter = collections.Counter()

    # copy assets
    output_assets_dir = os.path.join(output_dir, 'assets')
    if not os.path.exists(output_assets_dir):
        shutil.copytree(
            os.path.join(templates_dir, 'assets'),
            os.path.join(output_dir, 'assets'),
        )

    # render per-page templates
    template = template_lookup.get_template("result.html")
    for fname in os.listdir(data_dir):
        if not fname.endswith(".json"):
            continue

        data_path = os.path.join(data_dir, fname)
        data = json.load(open(data_path))
        context = {
            'url': data["url"],
            'info': data,
            'report': data,
            'get_code_info': get_code_info,
            'color_classes': COLOR_CLASSES,
        }
        rendered_html = template.render(**context)
        # replace `.json` with `.html`
        fname = fname[:-5] + ".html"
        html_path = os.path.join(output_dir, fname)
        with open(html_path, "w") as f:
            f.write(rendered_html)

        data["filename"] = fname
        pages.append(data)
        for count_key in ("total", "error", "warning", "notice"):
            counter[count_key] += data["count"][count_key]

    # render index template
    index_template = template_lookup.get_template("index.html")
    context = {
        'pages': pages,
        'counter': counter,
    }
    rendered_html = index_template.render(**context)
    html_path = os.path.join(output_dir, "index.html")
    with open(html_path, 'w') as f:
        f.write(rendered_html)


if __name__ == "__main__":
    main()
