#!/usr/bin/env bash
#
# Copyright (c) 2012 Mathieu Turcotte
# Licensed under the MIT license.

pep8 *.py
python msparser_test.py --verbose
