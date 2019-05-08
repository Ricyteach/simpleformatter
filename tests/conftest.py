#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Share fixtures for `simpleformatter` package."""
from copy import deepcopy

import pytest
import simpleformatter

global_simpleformatter = simpleformatter.simpleformatter


@pytest.fixture
def sf_copy():
    return deepcopy(global_simpleformatter)


@pytest.fixture
def formattable(sf_copy):
    return sf_copy.formattable


@pytest.fixture
def formatmethod():
    return simpleformatter.formatmethod


@pytest.fixture
def target(sf_copy):
    return sf_copy.target
