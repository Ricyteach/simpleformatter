#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for suffix matched format specifiers, eg '.3ft' resolving to the 'ft' target."""

import pytest

from simpleformatter import SimpleFormatter, formatmethod

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


# --- suffix matching on formatmethod ------------------------------------------------------------------------------


@pytest.fixture
def Data(sf):
    """the classic bytes/KB/MB/GB formatmethod example, with suffix matching"""

    @sf.formattable
    class Data(float):

        @formatmethod('Bytes', 'B', suffix=True)
        def _repr_b_(self, spec, std_spec):
            return f'{float(self):{std_spec}} {spec}'

        @formatmethod('KB', suffix=True)
        def _repr_kb_(self, spec, std_spec):
            return f'{self / 1024:{std_spec}} {spec}'

        @formatmethod('MB', suffix=True)
        def _repr_mb_(self, spec, std_spec):
            return f'{self / 1024 ** 2:{std_spec}} {spec}'

    return Data


def test_formatmethod_suffix_splits_the_spec(Data):
    assert f"{Data(112_113_254):.2fMB}" == '106.92 MB'


def test_formatmethod_suffix_with_no_standard_spec(Data):
    assert f"{Data(112_113_254):MB}" == '106.91953086853027 MB'


def test_formatmethod_longest_suffix_wins_across_methods(Data):
    """'KB' and 'MB' must beat the shorter 'B', even though they are on different methods"""

    assert f"{Data(112_113_254):.0fB}" == '112113254 B'
    assert f"{Data(112_113_254):.0fKB}" == '109486 KB'
    assert f"{Data(112_113_254):.0fMB}" == '107 MB'


def test_formatmethod_suffix_supports_the_whole_mini_language(Data):
    assert f"{Data(112_113_254):>14.2fMB}" == '        106.92 MB'


def test_formatmethod_unmatched_spec_falls_back_to_the_original_format(Data):
    assert f"{Data(112_113_254):.2f}" == '112113254.00'


def test_exact_formatmethod_beats_suffix_formatmethod(sf):

    @sf.formattable
    class C:

        @formatmethod('.3ft')
        def exact(self):
            return "exact"

        @formatmethod('ft', suffix=True)
        def suffixed(self, spec, std_spec):
            return "suffix"

    assert f"{C():.3ft}" == "exact"
    assert f"{C():.9ft}" == "suffix"


def test_suffix_formatmethod_with_override_beats_a_target(sf):

    @sf.target('ft', suffix=True)
    def from_target(obj, spec, std_spec):
        return "target"

    @sf.formattable
    class C:

        @formatmethod('ft', suffix=True, override=True)
        def from_method(self, spec, std_spec):
            return "method"

    assert f"{C():.3ft}" == "method"


def test_suffix_formatmethod_without_override_loses_to_a_target(sf):
    """matching the documented order: targets sit above a formatmethod that has not asked to override"""

    @sf.target('ft', suffix=True)
    def from_target(obj, spec, std_spec):
        return "target"

    @sf.formattable
    class C:

        @formatmethod('ft', suffix=True)
        def from_method(self, spec, std_spec):
            return "method"

    assert f"{C():.3ft}" == "target"


def test_two_argument_suffix_formatmethod_receives_the_matched_spec(sf):

    @sf.formattable
    class C:

        @formatmethod('ft', 'cm', suffix=True)
        def two_arg(self, spec):
            return f"matched {spec}"

    assert f"{C():.3ft}" == "matched ft"
    assert f"{C():cm}" == "matched cm"


def test_empty_formatmethod_spec_is_never_a_suffix(sf):
    """an empty specifier would otherwise match every format spec there is"""

    @sf.formattable
    class C:

        @formatmethod(suffix=True)
        def default(self):
            return "default"

    assert f"{C()}" == "default"
    with pytest.raises(TypeError):
        f"{C():anything}"
