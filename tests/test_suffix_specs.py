#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for suffix matched format specifiers, eg '.3ft' resolving to the 'ft' target."""

import pytest

from simpleformatter import SimpleFormatter

LENGTHS = {'in': 1, 'ft': 1 / 12, 'cm': 2.54, 'mm': 25.4, 'm': 0.0254}


@pytest.fixture
def sf():
    return SimpleFormatter()


@pytest.fixture
def Inches(sf):
    """a formattable float carrying the length conversion targets"""

    @sf.target(*LENGTHS, suffix=True)
    def convert(value, unit, std_spec):
        return f'{LENGTHS[unit] * value:{std_spec}} {unit}'

    @sf.formattable
    class Inches(float): ...

    return Inches


def test_suffix_match_splits_the_spec(Inches):
    """the '.3' is applied by the standard machinery, the 'ft' selects the target"""

    assert f"{Inches(8.45):.3ft}" == '0.704 ft'


def test_suffix_match_with_no_standard_spec(Inches):
    assert f"{Inches(12):in}" == '12.0 in'


def test_longest_suffix_wins(Inches):
    """'mm' and 'cm' must both beat the shorter 'm'"""

    assert f"{Inches(1):mm}" == '25.4 mm'
    assert f"{Inches(1):cm}" == '2.54 cm'
    assert f"{Inches(1):m}" == '0.0254 m'


def test_standard_spec_supports_the_whole_mini_language(Inches):
    assert f"{Inches(12):>12.2fmm}" == '      304.80 mm'


def test_unmatched_spec_falls_back_to_the_original_format(Inches):
    """'.2f' matches no registered suffix, so float.__format__ handles it"""

    assert f"{Inches(8.45):.2f}" == '8.45'


def test_exact_match_beats_suffix_match(sf):

    @sf.target('ft', suffix=True)
    def suffixed(obj, spec, std_spec):
        return "suffix"

    @sf.target('.3ft')
    def exact(obj, spec):
        return "exact"

    @sf.formattable
    class C: ...

    assert f"{C():.3ft}" == "exact"
    assert f"{C():.9ft}" == "suffix"


def test_two_argument_suffix_target_receives_the_matched_spec(sf):

    @sf.target('ft', 'cm', suffix=True)
    def two_arg(obj, spec):
        return f"matched {spec}"

    @sf.formattable
    class C: ...

    assert f"{C():.3ft}" == "matched ft"
    assert f"{C():cm}" == "matched cm"


def test_bare_suffix_target_registers_the_empty_spec_exactly(sf):
    """an empty specifier would be a suffix of every format spec, so it stays an exact match"""

    @sf.target(suffix=True)
    def default(obj):
        return "default"

    @sf.formattable
    class C: ...

    assert sf.suffix_reg == {}
    assert f"{C()}" == "default"


def test_suffix_registries_do_not_leak_between_instances():
    """C only knows about sf2, so sf1's 'ft' suffix must not reach it -- the spec falls through to
    object.__format__, which rejects any non-empty spec"""

    sf1, sf2 = SimpleFormatter(), SimpleFormatter()

    @sf1.target('ft', suffix=True)
    def only_sf1(obj, spec, std_spec):
        return "sf1"

    @sf2.formattable
    class C: ...

    assert sf2.suffix_reg == {}
    with pytest.raises(TypeError):
        f"{C():.3ft}"


def test_suffix_specs_must_be_strings(sf):
    with pytest.raises(TypeError):
        @sf.target(object(), suffix=True)
        def f(): ...
