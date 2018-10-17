.PHONY: clean clean-data clean-html develop install quality requirements requirements.js test

requirements: requirements.js
	pip install --quiet --upgrade -r requirements.txt --exists-action w

requirements.js:
	npm install

install: requirements
	python setup.py install

develop: install
	pip install --quiet --upgrade -r dev-requirements.txt --exists-action w
	pip install --editable .

clean:
	find . -name '*.pyc' -delete

clean-data:
	rm -rf data

clean-html:
	rm -rf html

test: clean
	scrapy check edx
	pytest --cov=./

quality: develop
	pycodestyle pa11ycrawler
	pylint pa11ycrawler
