# Copyright (c) 2012 Mathieu Turcotte
# Licensed under the MIT license.

publish: test
	python setup.py sdist upload

test: lint
	python msparser_test.py --verbose

lint:
	pep8 *.py

clean:
	rm -rvf __pycache__ *.pyc

.PHONY: publish test lint clean
