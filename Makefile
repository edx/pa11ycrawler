.PHONY: requirements

requirements: requirements.js
	pip install --quiet --upgrade -r requirements.txt --exists-action w

requirements.js:
	npm install

install: requirements

develop: requirements
	pip install --quiet --upgrade -r dev-requirements.txt --exists-action w

clean:
	find . -name '*.pyc' -delete

test: clean
	scrapy check edx
	py.test

quality:
	pycodestyle pa11ycrawler
	pylint pa11ycrawler
