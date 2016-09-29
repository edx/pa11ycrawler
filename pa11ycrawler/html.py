"""
This script transforms JSON from the pa11ycrawler into a beautiful HTML
report.
"""
import re
import argparse
import json
import logging
import collections
from path import Path
from jinja2 import Environment, PackageLoader
from pa11ycrawler.util import pa11y_counts

log = logging.getLogger(__name__)

PARENT_DIR = Path(__file__).abspath().parent
REPO_DIR = PARENT_DIR.parent

# A WCAG ref consists of one or more uppercase letters followed by one or more
# digits. For example, "F77", "G73", "ARIA1".
# The `code` that pa11y provides may have several WCAG refs -- if so, they are
# separated by commas with no space in between.
# For example, "H77,H78,H79,H80,H81"
WCAG_REFS_RE = re.compile("[A-Z]+[0-9]+(,[A-Z]+[0-9]+)*")


def make_parser():
    """
    Returns an argparse instance for this script.
    """
    parser = argparse.ArgumentParser(description="generate HTML from crawler JSON")
    parser.add_argument(
        "--data-dir", default="data",
        help="Directory containing JSON data from crawler [%(default)s]"
    )
    parser.add_argument(
        "--output-dir", default="html",
        help="Directory to output the resulting HTML files [%(default)s]"
    )
    return parser


def main():
    """
    Validates script arguments and calls the render_html() function with them.
    """
    parser = make_parser()
    args = parser.parse_args()
    data_dir = Path(args.data_dir).expand()
    if not data_dir.isdir():
        msg = "Data directory {dir} does not exist".format(dir=args.data_dir)
        raise ValueError(msg)
    data_filenames = [name for name in data_dir.files()
                      if name.endswith(".json")]
    if not data_filenames:
        msg = "Data directory {dir} contains no JSON files".format(dir=args.data_dir)
        raise ValueError(msg)
    output_dir = Path(args.output_dir).expand()
    output_dir.makedirs_p()

    return render_html(data_dir, output_dir)


def wcag_refs(code):
    """
    Given a `code` from pa11y, return a list of the WCAG references.
    These references are always of the form: one or more capital letters,
    followed by one or more digits. One `code` may contain multiple
    references, separated by commas.
    """
    bits = code.split(".")
    for bit in reversed(bits):
        if WCAG_REFS_RE.match(bit):
            return bit.split(",")
    return []


def copy_assets(output_dir):
    """
    Copy static assets (CSS, JS, fonts, etc) into the output directory.
    """
    (PARENT_DIR / "templates" / "assets").merge_tree(output_dir / "assets")


def render_html(data_dir, output_dir):
    """
    The main workhorse of this script. Finds all the JSON data files
    from pa11ycrawler, and transforms them into HTML files via Jinja2 templating.
    """
    env = Environment(loader=PackageLoader('pa11ycrawler', 'templates'))
    env.globals["wcag_refs"] = wcag_refs
    pages = []
    counter = collections.Counter()

    copy_assets(output_dir)

    # render detail templates
    template = env.get_template("detail.html")
    for data_file in data_dir.files('*.json'):
        data = json.load(data_file.open())
        num_error, num_warning, num_notice = pa11y_counts(data['pa11y'])
        data["num_error"] = num_error
        data["num_warning"] = num_warning
        data["num_notice"] = num_notice
        rendered_html = template.render(**data)  # pylint: disable=no-member
        # replace `.json` with `.html`
        fname = data_file.namebase + ".html"
        html_path = output_dir / fname
        html_path.write_text(rendered_html, encoding='utf-8')

        data["filename"] = fname
        pages.append(data)

        counter["error"] += num_error
        counter["warning"] += num_warning
        counter["notice"] += num_notice

    def extract_nums(page):
        "Used for sorting"
        return (
            page["num_error"],
            page["num_warning"],
            page["num_notice"],
        )

    # render index template
    index_template = env.get_template("index.html")
    context = {
        "pages": sorted(pages, key=extract_nums, reverse=True),
        "num_error": counter["error"],
        "num_warning": counter["warning"],
        "num_notice": counter["notice"],
    }
    rendered_html = index_template.render(**context)  # pylint: disable=no-member
    html_path = output_dir / "index.html"
    html_path.write_text(rendered_html, encoding='utf-8')


if __name__ == "__main__":
    main()
