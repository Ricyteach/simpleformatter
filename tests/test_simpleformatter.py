#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `simpleformatter` package."""

from collections import defaultdict
import pytest

empty_str = ""  # for readability


@pytest.fixture
def simpleformatter():
    """reimport fresh copy of the module each time"""
    import simpleformatter
    return simpleformatter


@pytest.fixture
def SimpleFormatterError(simpleformatter):
    from simpleformatter.simpleformatter import SimpleFormatterError
    return SimpleFormatterError


# example api implementation fixtures ##################################################################################
#
# NOTE: each example class fixture has its own test_results dictionary (defaultdict) that contains the expected test
# results for a given format_spec, e.g.:
#
#                                spec      expected result
#                                -----     ---------------
#                   test_results["foo"] = "fooed result"
#                   test_results["bar"] = "barred result"
#
# The dictionary returns None for a format_spec that isn't expected; when a format_spec isn't expected, behavior falls
# back on default/parent behavior upon application of the formatter function (such as format, an f-string, a Formatter,
# or string.format). If fallback behavior raises an exception, the exception will raise *FROM* and SimpleFormatterError.


@pytest.fixture
def A(simpleformatter):
    class A(simpleformatter.SimpleFormattable):
        """A class that has a custom formatting function decorated by simpleformatter

        the function accepts no arguments so no spec is allowed other than the default, empty_str"""
        test_results = defaultdict(lambda: None)

        # my_formatter expected results
        test_results[empty_str] = "class A object formatted"  # no spec argument equivalent to empty_str

        @simpleformatter.simpleformatter
        def my_formatter(self):
            return str(self) + " formatted"

        def __str__(self):
            return "class A object"

    return A


@pytest.fixture
def example_a(A):
    return A()


@pytest.fixture
def B(simpleformatter):
    class B(simpleformatter.SimpleFormattable):
        """A class that has a custom formatting function decorated by simpleformatter, with spec = 'special_'"""
        test_results = defaultdict(lambda: None)

        # specialx_formatter expected results
        test_results[empty_str] = "class B object spec = ''"
        test_results["specialx"] = "class B object spec = 'specialx'"

        # specialyz_formatter expected results
        test_results["specialy"] = "class B object spec = 'specialyz'"
        test_results["specialz"] = "class B object spec = 'specialyz'"

        @simpleformatter.simpleformatter
        @simpleformatter.simpleformatter(spec="specialx")
        def specialx_formatter(self, spec):
            return f"class B object spec = {spec!r}"

        @simpleformatter.simpleformatter(spec="specialy")
        @simpleformatter.simpleformatter(spec="specialz")
        def specialyz_formatter(self):
            return str(self) + " spec = 'specialyz'"

        def __str__(self):
            return "class B object"

    return B


@pytest.fixture
def example_b(B):
    return B()


@pytest.fixture
def C(simpleformatter):
    class C(simpleformatter.SimpleFormattable):
        """A class that has a custom formatting function decorated by simpleformatter, with spec = 'special_'"""
        test_results = defaultdict(lambda: None)

        # parent formatter is == format function
        test_results[""] = "class C object"

        # special_formatter expected results
        test_results["specialx"] = "class C object spec = 'specialx'"
        test_results["specialy"] = "class C object spec = 'specialy'"
        test_results["specialz"] = "class C object spec = 'specialz'"

        @simpleformatter.simpleformatter(spec="specialx")
        @simpleformatter.simpleformatter(spec="specialy")
        @simpleformatter.simpleformatter(spec="specialz")
        def special_formatter(self, spec):
            return f"class C object spec = {spec!r}"

        def __str__(self):
            return "class C object"

    return C


@pytest.fixture
def example_c(C):
    return C()


@pytest.fixture
def D(simpleformatter):
    class D(simpleformatter.SimpleFormattable):
        """A class that assigns a custom external Formatter api object"""
        # TODO: figure out if this makes sense
        pass

    return D


@pytest.fixture
def example_d(D):
    return D()


### example fixture tests (does NOT test the api!!) ####################################################################

@pytest.mark.parametrize("cls_name, formatter_name, spec", [
    ("A", "A.my_formatter", empty_str),
    ("A", "A.my_formatter", "spec"),
    ("B", "B.specialx_formatter", empty_str),
    ("B", "B.specialx_formatter", "specialx"),
    ("B", "B.specialyz_formatter", "specialy"),
    ("B", "B.specialyz_formatter", "specialz"),
    ("C", "format", empty_str),  # parent formatter is == format function
    ("C", "C.special_formatter", "specialx"),
    ("C", "C.special_formatter", "specialy"),
    ("C", "C.special_formatter", "specialz"),
], ids=[
    "A.my_formatter empty_str", "A.my_formatter 'spec'",
    "B.my_formatter empty_str", "B.specialx_formatter", "B.specialyz_formatter y", "B.specialyz_formatter z",
    "C.my_formatter empty_str", "C.special_formatter x", "C.special_formatter y", "C.special_formatter z",
])
def test_formatter_function(cls_name, formatter_name, spec, A, example_a, B, example_b, C, example_c):
    """Does not test the api!!!! Makes sure the formatter_name functions for test suite example classes are working"""
    cls = eval(cls_name)
    obj = eval(f"example_{cls_name.lower()}")
    formatter = eval(formatter_name)
    result = cls.test_results[spec]
    if result is None:
        # invalid spec; just make sure no exceptions get raised when formatter_name is called
        try:
            formatter(obj, spec)
        except TypeError:
            formatter(obj)
    else:
        try:
            assert formatter(obj, spec) == result
        except TypeError:
            assert formatter(obj) == result


### api tests ##########################################################################################################

@pytest.mark.parametrize("cls_name, spec", [
    ("A", empty_str),
    ("A", "spec"),
    ("B", empty_str),
    ("B", "specialx"),
    ("B", "specialy"),
    ("B", "specialz"),
    ("C", empty_str),  # parent formatter is == format function
    ("C", "specialx"),
    ("C", "specialy"),
    ("C", "specialz"),
], ids=[
    "A.my_formatter empty_str", "A.my_formatter 'spec'",
    "B.my_formatter empty_str", "B.specialx_formatter", "B.specialyz_formatter y", "B.specialyz_formatter z",
    "C.my_formatter empty_str", "C.special_formatter x", "C.special_formatter y", "C.special_formatter z",
])
def test_simpleformatter_api(cls_name, spec, A, example_a, B, example_b, C, example_c):
    """The actual api tested here"""
    cls = eval(cls_name)
    obj = eval(f"example_{cls_name.lower()}")
    result = cls.test_results[spec]
    if result is None:
        with pytest.raises(TypeError):
            if spec is None:
                f"{obj}"
            else:
                f"{obj:{spec!s}}"
    else:
        if spec is None:
            assert f"{obj}" == result
        else:
            assert f"{obj:{spec!s}}" == result


def test_ambiguous_no_spec(simpleformatter):
    """having two competing functions for no format spec is ambiguous"""

    with pytest.raises(SimpleFormatterError):
        class X(simpleformatter.SimpleFormattable):

            @simpleformatter.simpleformatter
            def a(self): ...

            @simpleformatter.simpleformatter
            def b(self): ...


def test_ambiguous_competing(simpleformatter):
    """having two competing functions for SAME format spec is ambiguous"""

    with pytest.raises(SimpleFormatterError):
        class X(simpleformatter.SimpleFormattable):

            @simpleformatter.simpleformatter("spec")
            def a(self): ...

            @simpleformatter.simpleformatter("spec")
            def b(self): ...


def test_ambiguous_special(simpleformatter):
    """having two functions, one with no spec and one with empty_str spec is ambiguous"""

    with pytest.raises(SimpleFormatterError):
        class X(simpleformatter.SimpleFormattable):

            @simpleformatter.simpleformatter
            def a(self): ...

            @simpleformatter.simpleformatter(empty_str)
            def b(self): ...
