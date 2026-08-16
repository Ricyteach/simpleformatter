#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Doctest support for the `simpleformatter` package modules.

`formattable` and `target` are bound methods of a `SimpleFormatter` instance created in `__init__.py`, so they are not
in the namespace of `simpleformatter/simpleformatter.py` where most of the docstrings live. This makes them available
to the doctests anyway.
"""

import pytest

import simpleformatter


@pytest.fixture(autouse=True)
def _doctest_api(doctest_namespace):
    """Expose the public API decorators to module doctests.

    Each doctest gets its own SimpleFormatter so registrations made in one docstring cannot leak into the next.
    """

    sf = simpleformatter.SimpleFormatter()
    doctest_namespace["simpleformatter"] = sf
    doctest_namespace["formattable"] = sf.formattable
    doctest_namespace["target"] = sf.target
    doctest_namespace["formatmethod"] = simpleformatter.formatmethod
