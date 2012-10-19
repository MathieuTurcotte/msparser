# Copyright (c) 2011 Mathieu Turcotte
# Licensed under the MIT license.

from distutils.core import setup


def read(path):
    return open(path).read()


setup(
    name="msparser",
    py_modules=["msparser"],
    version="1.3",
    license="MIT",
    description="Valgrind massif.out parser",
    long_description=read("README.rst"),
    author="Mathieu Turcotte",
    author_email="turcotte.mat@gmail.com",
    url="https://github.com/MathieuTurcotte/msparser",
    keywords=["valgrind", "massif", "parser"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: General",
    ]
)
