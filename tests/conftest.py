#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Share fixtures for `simpleformatter` package."""

import pytest


@pytest.fixture
def simpleformatter():
    """reimport fresh copy of the module each time"""
    import simpleformatter
    return simpleformatter


@pytest.fixture
def SimpleFormatterError(simpleformatter):
    from simpleformatter.simpleformatter import SimpleFormatterError
    return SimpleFormatterError

@pytest.fixture
def formattable(simpleformatter):
    return simpleformatter.formattable


@pytest.fixture
def method(simpleformatter):
    return simpleformatter.method


@pytest.fixture
def function(simpleformatter):
    return simpleformatter.function

