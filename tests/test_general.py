#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `simpleformatter.target` decorator usage."""

from collections import defaultdict

import pytest


@pytest.fixture
def gen_fmtr_func1():
    def univ_formatter1(obj, spec):
        return f"{obj!s} with univ spec #1 = {spec!r}"
    return univ_formatter1


@pytest.fixture
def gen_fmtr_func2():
    def univ_formatter2(obj, spec):
        return f"{obj!s} with univ spec #2 = {spec!r}"
    return univ_formatter2


@pytest.fixture
def A():
    class A:
        test_results=defaultdict(lambda: None)
        test_results.update(spec1="class A object with univ spec #1 = 'spec1'",
                            spec2="class A object with univ spec #2 = 'spec2'", ),
        def __str__(self):
            return "class A object"
    return A


@pytest.fixture
def a_first(formattable, A):
    """class A decorated first"""
    return formattable(A)()


@pytest.fixture
def formatters_first(target, gen_fmtr_func1, gen_fmtr_func2):
    """Formatter functions decorated first"""
    return target("spec1")(gen_fmtr_func1), target(gen_fmtr_func2, "spec2")


@pytest.fixture
def a_last(formattable, formatters_first, A):
    """class A decorated last"""
    return formattable(A)()


@pytest.fixture
def formatters_last(target, a_first, gen_fmtr_func1, gen_fmtr_func2):
    """Formatter functions decorated last"""
    target("spec1")(gen_fmtr_func1)
    target(gen_fmtr_func2, "spec2")
    return


@pytest.mark.parametrize("spec", [
    "spec1",
    "spec2",
])
def test_class_first(a_first, formatters_last, spec):
    expected = a_first.test_results[spec]
    actual = f"{a_first:{spec!s}}"
    assert actual == expected


@pytest.mark.parametrize("spec", [
    "spec1",
    "spec2",
])
def test_formatters_first(a_last, formatters_first, spec):
    f"{a_last:{''}}"
    assert f"{a_last:{spec!s}}" == a_last.test_results[spec]


def test_wrong_use_of_function(formattable, target):
    """Class methods should be decorated with formatmethod"""
    with pytest.raises(TypeError):
        @formattable
        class X:
            @target
            def x(self):
                ...

@pytest.mark.parametrize("bad_arg", [
    None, 1, object(),
], ids= ("NoneType", "int", "object()"))
def test_str_only_spec(bad_arg, target, formatmethod, formattable):
    """format specs must be strings (might change this requirement later...?)"""
    with pytest.raises(TypeError):
        @target(bad_arg)
        def f(): ...
    with pytest.raises(TypeError):
        @formattable
        class X:
            @formatmethod(bad_arg)
            def f(self): ...


def test_not_callable(target, formatmethod):
    """target and formatmethod decorators apply only to callables"""
    with pytest.raises(TypeError):
        target(1)
    with pytest.raises(TypeError):
        formatmethod(1)


def test_not_type(formattable):
    with pytest.raises(TypeError):
        formattable(int)
