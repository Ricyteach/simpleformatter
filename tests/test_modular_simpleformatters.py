#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for multiple, concurrent instances of the `SimpleFormatter` class."""
import pytest


@pytest.fixture
def SimpleFormatter(simpleformatter):
    return simpleformatter.SimpleFormatter


@pytest.fixture
def sf1(SimpleFormatter):
    return SimpleFormatter()


@pytest.fixture
def sf2(SimpleFormatter):
    return SimpleFormatter()


@pytest.fixture
def obj1(sf1):
    @sf1.formattable
    class Obj1: ...
    return Obj1()


@pytest.fixture
def func1(sf1):
    @sf1.function
    def f1(obj):
        return "f1"
    return f1


@pytest.fixture
def obj2(sf2):
    @sf2.formattable
    class Obj2: ...
    return Obj2()


@pytest.fixture
def func2(sf2):
    @sf2.function
    def f2(obj):
        return "f2"
    return f2


def test_modular(obj1, func1, obj2, func2):
    assert f"{obj1}" == "f1"
    assert f"{obj2}" == "f2"
