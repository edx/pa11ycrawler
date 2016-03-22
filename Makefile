.PHONY: requirements

requirements: requirements.js
	pip install -q -r requirements/base.txt --exists-action w

requirements.js:
	npm install

requirements.test: requirements
	pip install -q -r requirements/test.txt --exists-action w

install: requirements

develop: requirements.test

clean:
	find . -name '*.pyc' -delete

test: clean
	nosetests pa11ycrawler --with-coverage --cover-package=pa11ycrawler

quality:
	pep8 pa11ycrawler
	pylint pa11ycrawler
