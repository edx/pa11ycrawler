.PHONY: requirements

requirements: requirements.js
	pip install .

requirements.js:
	npm install

install: requirements

develop: requirements
	pip install -U pytest>=2.7 pytest-mock pycodestyle pylint edx-lint==0.5.1

clean:
	find . -name '*.pyc' -delete

test: clean
	scrapy check local-edx
	py.test

quality:
	pycodestyle pa11ycrawler
	pylint pa11ycrawler
