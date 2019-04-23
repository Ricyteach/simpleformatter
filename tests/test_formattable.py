#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `simpleformatter` package."""

from collections import defaultdict
import pytest

empty_str = ""  # for readability

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
# or string.format). If fallback behavior raises an exception, the exception will raise *FROM* a SimpleFormatterError.


@pytest.fixture
def A(simpleformatter):
    @simpleformatter.formattable
    class A:
        """A class that has a custom formatting function decorated by simpleformatter

        the uncalled decorator means the default format spec, which is empty_str

        the function accepts only a self argument (ie, it expects no spec argument)"""
        test_results = defaultdict(lambda: None)

        # my_formatter expected results
        test_results[empty_str] = "class A object formatted"  # no spec argument equivalent to empty_str

        @simpleformatter.method  # no spec argument equivalent to empty_str
        def my_formatter(self):
            return str(self) + " formatted"

        def __str__(self):
            return "class A object"

    return A


@pytest.fixture
def ex_a(A):
    return A()


@pytest.fixture
def B(simpleformatter):
    @simpleformatter.formattable
    class B:
        """A class that has doubly decorated custom formatting functions, different with specs"""
        test_results = defaultdict(lambda: None)

        # specialx_formatter expected results
        test_results[empty_str] = "class B object spec = ''"
        test_results["specialx"] = "class B object spec = 'specialx'"

        # specialyz_formatter expected results
        test_results["specialy"] = "class B object spec = 'specialyz'"
        test_results["specialz"] = "class B object spec = 'specialyz'"

        @simpleformatter.method
        @simpleformatter.method("specialx")
        def specialx_formatter(self, spec):
            return f"class B object spec = {spec!r}"

        @simpleformatter.method("specialy")
        @simpleformatter.method("specialz")
        def specialyz_formatter(self):
            return str(self) + " spec = 'specialyz'"

        def __str__(self):
            return "class B object"

    return B


@pytest.fixture
def ex_b(B):
    return B()


@pytest.fixture
def C(simpleformatter):
    @simpleformatter.formattable
    class C:
        """A class that has multiple-decorated custom formatting function

        for this one, the empty_str spec falls back on default __format__ functionality"""
        test_results = defaultdict(lambda: None)

        # parent formatter is == object.__format__ function (~equivalent to format() built-in)
        test_results[""] = "class C object"

        # special_formatter expected results
        test_results["specialx"] = "class C object spec = 'specialx'"
        test_results["specialy"] = "class C object spec = 'specialy'"
        test_results["specialz"] = "class C object spec = 'specialz'"

        @simpleformatter.method("specialx")
        @simpleformatter.method("specialy")
        @simpleformatter.method("specialz")
        def special_formatter(self, spec):
            return f"class C object spec = {spec!r}"

        # the object.__format__ function just returns obj.__str__
        def __str__(self):
            return "class C object"

    return C


@pytest.fixture
def ex_c(C):
    return C()


# noinspection PyTypeChecker
@pytest.fixture
def D(simpleformatter, my_formatter):

    @simpleformatter.formattable(spec=my_formatter)
    class D:
        """api decorated class, with externally defined formatting"""
        test_results = defaultdict(lambda: None)

        # parent formatter is == object.__format__ function (~equivalent to format() built-in)
        test_results[empty_str] = "class D object"

        # my_formatter expected results
        test_results["spec"] = "class D object formatted"

        # the object.__format__ function just returns obj.__str__
        def __str__(self):
            return "class D object"

    return D


@pytest.fixture
def ex_d(D):
    return D()


@pytest.fixture
def E(simpleformatter):
    @simpleformatter.formattable
    class E:
        """A class that assigns a custom external Formatter api object"""
        # TODO: figure out if this makes sense
        pass

    return E


@pytest.fixture
def ex_e(E):
    return E()


@pytest.fixture
def my_formatter():
    def my_formatter(obj, spec):
        return f"class {type(obj).__qualname__[-1]} object formatted"
    return my_formatter


# example fixture tests (does NOT test the api!!); verify formatter functions are "working" ############################

@pytest.mark.parametrize("cls_name, formatter_name, spec", [
    ("A", "A.my_formatter", empty_str),  # no argument to simpleformatter decorator == empty_str format spec
    ("A", "A.my_formatter", "spec"),
    ("B", "B.specialx_formatter", empty_str),  # no argument to simpleformatter decorator == empty_str format spec
    ("B", "B.specialx_formatter", "specialx"),
    ("B", "B.specialyz_formatter", "specialy"),
    ("B", "B.specialyz_formatter", "specialz"),
    ("C", "format", empty_str),  # parent formatter is == format function
    ("C", "C.special_formatter", "specialx"),
    ("C", "C.special_formatter", "specialy"),
    ("C", "C.special_formatter", "specialz"),
    ("D", "format", empty_str),  # no argument to simpleformatter decorator == empty_str format spec
    ("D", "my_formatter", "spec"),
], ids=[
    "A.my_formatter empty_str", "A.my_formatter 'spec'",
    "B.my_formatter empty_str", "B.specialx_formatter", "B.specialyz_formatter y", "B.specialyz_formatter z",
    "C.my_formatter empty_str", "C.special_formatter x", "C.special_formatter y", "C.special_formatter z",
    "D -> my_formatter empty_str", "D -> my_formatter 'spec'",
])
def test_formatter_function(cls_name, formatter_name, spec, A, ex_a, B, ex_b, C, ex_c, D, ex_d, my_formatter):
    """Does not test the api!!!! Makes sure the formatter_name functions for test suite example classes are working"""
    cls = eval(cls_name)
    obj = eval(f"ex_{cls_name.lower()}")
    formatter = eval(formatter_name)
    result = cls.test_results[spec]
    if result is None:
        # invalid spec; just make sure no exceptions get raised when formatter_name is called
        try:
            formatter(obj, spec)
        except TypeError:
            # single argument
            formatter(obj)
    else:
        try:
            assert formatter(obj, spec) == result
        except TypeError:
            # single argument
            assert formatter(obj) == result


# api tests ############################################################################################################

@pytest.mark.parametrize("cls_name, spec", [
    ("A", empty_str),  # no argument to simpleformatter decorator == empty_str format spec
    ("A", "spec"),
    ("B", empty_str),  # no argument to simpleformatter decorator == empty_str format spec
    ("B", "specialx"),
    ("B", "specialy"),
    ("B", "specialz"),
    ("C", empty_str),  # parent formatter is == format function
    ("C", "specialx"),
    ("C", "specialy"),
    ("C", "specialz"),
    ("D", empty_str),  # no argument to simpleformatter decorator == empty_str format spec
    ("D", "spec"),
], ids=[
    "A.my_formatter empty_str", "A.my_formatter 'spec'",
    "B.my_formatter empty_str", "B.specialx_formatter", "B.specialyz_formatter y", "B.specialyz_formatter z",
    "C.my_formatter empty_str", "C.special_formatter x", "C.special_formatter y", "C.special_formatter z",
    "D -> my_formatter empty_str", "D -> my_formatter 'spec'",
])
def test_simpleformatter_api(cls_name, spec, A, ex_a, B, ex_b, C, ex_c, D, ex_d, my_formatter):
    """The actual api tested here"""
    cls = eval(cls_name)
    obj = eval(f"ex_{cls_name.lower()}")
    result = cls.test_results[spec]
    if result is None:
        with pytest.raises(TypeError):
            f"{obj:{spec!s}}"
    else:
        assert f"{obj:{spec!s}}" == result


def test_ambiguous_no_spec_and_inheritance(simpleformatter):
    """last defined spec wins with competing functions"""

    @simpleformatter.formattable
    class X:

        @simpleformatter.method
        def a(self):
            return "a"

        @simpleformatter.method
        def b(self):
            return "b"

    assert f"{X()}" == X().b()

    @simpleformatter.formattable
    class Y(X):

        @simpleformatter.method
        def c(self):
            return "c"

    assert f"{Y()}" == Y().c()

    @simpleformatter.formattable
    class Z(Y):

        @simpleformatter.method
        def c(self):
            return "d"

        @simpleformatter.method
        def c(self):
            return "e"

    assert f"{Z()}" == "e"


def test_ambiguous_competing(simpleformatter):
    """last defined spec wins with two competing functions for SAME format spec"""

    @simpleformatter.formattable
    class X:

        @simpleformatter.method("spec")
        def a(self):
            return "a"

        @simpleformatter.method("spec")
        def b(self):
            return "b"

    assert f"{X():spec}" == X().b()


def test_ambiguous_special(simpleformatter):
    """last defined spec wins with two competing functions, one with no spec and one with empty_str spec"""

    @simpleformatter.formattable
    class X:

        @simpleformatter.method
        def a(self):
            return "a"

        @simpleformatter.method(empty_str)
        def b(self):
            return "b"

    assert f"{X()}" == X().b()
