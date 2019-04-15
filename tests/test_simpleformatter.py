#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `simpleformatter` package."""
from collections import defaultdict
from contextlib import nullcontext as noexception
from dataclasses import dataclass

import pytest


import simpleformatter
from simpleformatter.simpleformatter import SimpleFormatterError


class A(simpleformatter.SimpleFormattable):
    """A class that has a custom formatting function decorated by simpleformatter

    the function accepts no arguments so no spec is allowed"""
    test_results = defaultdict(lambda: None)
    test_results[None] = "class A object"
    # test_results[''] = "class A object"

    @simpleformatter.simpleformatter
    def my_formatter(self):
        return str(self)

    def __str__(self):
        return "class A object"


class B(simpleformatter.SimpleFormattable):
    """A class that has a custom formatting function decorated by simpleformatter, with spec = 'special'"""
    test_results = defaultdict(lambda: None)
    test_results["specialx"] = "class B object spec = 'specialx'"
    test_results["specialy"] = "class B object spec = 'specialy'"

    @simpleformatter.simpleformatter(spec="specialx")
    def specialx_formatter(self, spec):
        return f"class B object spec = {spec!r}"

    @simpleformatter.simpleformatter(spec="specialy")
    def specialy_formatter(self):
        return str(self) + " spec = 'specialy'"

    def __str__(self):
        return "class B object"


class C(simpleformatter.SimpleFormattable):
    """A class that assigns a custom external Formatter api object"""
    pass


@pytest.mark.parametrize("cls, formatter, spec",[
    (A, A.my_formatter, None),
    (A, A.my_formatter, ""),
    (A, A.my_formatter, "spec"),
    (B, B.specialx_formatter,""),
    (B, B.specialx_formatter,"''"),
    (B, B.specialx_formatter,"specialx"),
    (B, B.specialy_formatter,"specialy"),
], ids=[
    "A.my_formatter None", "A.my_formatter empty_str", "A.my_formatter 'spec'",
    "B.my_formatter empty_str", "B.specialx_formatter ''", "B.specialx_formatter", "B.specialy_formatter"
])
def test_formatter_function(cls, formatter, spec):
    """Does not test the api!!!! Just makes sure the formatter functions for test suite example classes are working"""
    c=cls()
    result = cls.test_results[spec]
    if result is None:
        # invalid spec; just make sure no exceptions get raised when formatter is called
        try:
            formatter(c, spec)
        except TypeError:
            formatter(c)
    else:
        try:
            assert formatter(c, spec) == result
        except TypeError:
            assert formatter(c) == result


@pytest.mark.parametrize("cls, spec",[
    (A, None),
    (A, ""),
    (A, "spec"),
    (B, ""),
    (B,"''"),
    (B, "specialx"),
    (B, "specialy"),
], ids=[
    "A.my_formatter None", "A.my_formatter empty_str", "A.my_formatter 'spec'",
    "B.my_formatter empty_str", "B.specialx_formatter ''", "B.specialx_formatter", "B.specialy_formatter"
])
def test_simpleformatter_api(cls, spec):
    """The actual api tested here"""
    c=cls()
    result = cls.test_results[spec]
    if result is None:
        with pytest.raises(TypeError):
            if spec is None:
                f"{c}"
            else:
                f"{c:{spec!s}}"
    else:
        if spec is None:
            assert f"{c}" == result
        else:
            assert f"{c:{spec!s}}" == result
