from setuptools import setup

setup(
    name='pa11ycrawler',
    version='0.0.4',
    package_data={
        'pa11ycrawler': [
            'templates/*.*',
            'templates/assets/js/*.*',
            'templates/assets/css/*.*',
        ]
    },
    packages=[
        'pa11ycrawler',
        'pa11ycrawler.spiders'
    ],
    install_requires=[
        'mako>=1.0.2',
        'scrapy>=1.0.5',
        'urlobject',
    ],
    test_require=[
        'pytest>=2.7',
        'pytest-mock',
        'pycodestyle',
        'edx-lint==0.5.1',
        'pylint',
    ],
    entry_points={
        'console_scripts': [
            'pa11ycrawler-html=pa11ycrawler.html:main',
        ]
    }
)
