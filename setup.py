from setuptools import setup

setup(
    name='pa11ycrawler',
    version='0.1',
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
        'lxml>=3.4.4',
        'mako>=1.0.2',
        'scrapy>=1.0.5',
    ],
    entry_points={
        'console_scripts': [
            'pa11ycrawler=pa11ycrawler.cmdline:main',
        ]
    },
)
