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
        test_results.update(spec1="class A object with univ spec #1 = 'spec1'", spec2="class A object with univ spec #2 = 'spec2'", ),
        def __str__(self):
            return "class A object"
    return A


@pytest.fixture
def A_first(formattable, A):
    """class A decorated first"""
    return formattable(A)


@pytest.fixture
def formatters_first(function, gen_fmtr_func1, gen_fmtr_func2):
    """Formatter functions decorated first"""
    return function("spec1")(gen_fmtr_func1), function(gen_fmtr_func2, "spec2")


@pytest.fixture
def A_last(formattable, formatters_first, A):
    """class A decorated last"""
    return formattable(A)


@pytest.fixture
def formatters_last(function, A_first, gen_fmtr_func1, gen_fmtr_func2):
    """Formatter functions decorated last"""
    return function("spec1")(gen_fmtr_func1), function(gen_fmtr_func2, "spec2")


@pytest.mark.parametrize("spec", [
    "spec1",
    "spec2",
], ids=["spec1", "spec2"])
def test_class_first(A_first, formatters_last, spec):
    assert f"{A_first:{spec}}" == A_first.test_results[spec]


@pytest.mark.parametrize("spec", [
    "spec1",
    "spec2",
], ids=["spec1", "spec2"])
def test_formatters_first(A_first, formatters_last, spec):
    assert f"{A_first:{spec}}" == A_first.test_results[spec]
