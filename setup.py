from setuptools import setup

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
    version='1.2.0',
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
    install_requires=get_requirements("requirements.txt"),
    tests_require=get_requirements("dev-requirements.txt"),
    entry_points={
        'console_scripts': [
            'pa11ycrawler-html=pa11ycrawler.html:main',
        ]
    }
)
