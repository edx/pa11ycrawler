from setuptools import setup

VERSION = '1.5.5'
DESCRIPTION = 'A Scrapy spider for a11y auditing Open edX installations.'
LONG_DESCRIPTION = """pa11ycrawler is a Scrapy spider that runs a Pa11y check
on every page of an Open edX installation,
to audit it for accessibility purposes."""


def is_requirement(line):
    line = line.strip()
    # Skip blank lines, comments, and editable installs
    return not (
        line == '' or
        line.startswith('--') or
        line.startswith('-r') or
        line.startswith('#') or
        line.startswith('-e') or
        line.startswith('git+')
    )


def get_requirements(path):
    with open(path) as f:
        lines = f.readlines()
    return [l.strip() for l in lines if is_requirement(l)]


setup(
    name='pa11ycrawler',
    version=VERSION,
    author='edX',
    author_email='oscm@edx.org',
    url='https://github.com/edx/pa11ycrawler',
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    package_data={
        'pa11ycrawler': [
            'templates/*.*',
            'templates/assets/js/*.*',
            'templates/assets/css/*.*',
        ]
    },
    packages=[
        'pa11ycrawler',
        'pa11ycrawler.pipelines',
        'pa11ycrawler.spiders',
    ],
    install_requires=get_requirements("requirements.txt"),
    tests_require=get_requirements("dev-requirements.txt"),
    license="Apache-2.0",
    entry_points={
        'console_scripts': [
            'pa11ycrawler-html=pa11ycrawler.html:main',
        ]
    }
)
