#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `simpleformatter` package.

NOTE: each example class has a test_results dictionary that contains the expected test results for a give format_spec

the dictionary returns None for a format_spec that isn't expected

when a format_spec isn't expected, either a TypeError is raised, or the default object.__format__ method is invoked

which of these two behaviors occurs depends on the value of OVERRIDE_OBJECT (True or False)
"""

from collections import defaultdict
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
def A(simpleformatter):

    class A(simpleformatter.SimpleFormattable):
        """A class that has a custom formatting function decorated by simpleformatter

        the function accepts no arguments so no spec is allowed"""
        test_results = defaultdict(lambda: None)
        test_results[None] = "class A object"
        # test_results[''] = "class A object"  <-- keep commented; only works if OVERRIDE_OBJECT==True

        @simpleformatter.simpleformatter
        def my_formatter(self):
            return str(self)

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

    return B


@pytest.fixture
def example_b(B):
    return B()


@pytest.fixture
def C(simpleformatter):

    class C(simpleformatter.SimpleFormattable):
        """A class that assigns a custom external Formatter api object"""
        # TODO: figure out if this makes sense
        pass

    return C


@pytest.fixture
def example_c(C):
    return C()


@pytest.mark.parametrize("cls_name, formatter_name, spec",[
    ("A", "A.my_formatter", None),
    ("A", "A.my_formatter", ""),
    ("A", "A.my_formatter", "spec"),
    ("B", "B.specialx_formatter",""),
    ("B", "B.specialx_formatter","''"),
    ("B", "B.specialx_formatter","specialx"),
    ("B", "B.specialy_formatter","specialy"),
], ids=[
    "A.my_formatter None", "A.my_formatter empty_str", "A.my_formatter 'spec'",
    "B.my_formatter empty_str", "B.specialx_formatter ''", "B.specialx_formatter", "B.specialy_formatter"
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


@pytest.mark.parametrize("cls_name, spec",[
    ("A", None),
    ("A", ""),
    ("A", "spec"),
    ("B", ""),
    ("B","''"),
    ("B", "specialx"),
    ("B", "specialy"),
], ids=[
    "A.my_formatter None", "A.my_formatter empty_str", "A.my_formatter 'spec'",
    "B.my_formatter empty_str", "B.specialx_formatter ''", "B.specialx_formatter", "B.specialy_formatter"
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
