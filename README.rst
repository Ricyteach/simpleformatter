===============
simpleformatter
===============

.. image:: https://github.com/Ricyteach/simpleformatter/actions/workflows/ci.yml/badge.svg
        :target: https://github.com/Ricyteach/simpleformatter/actions/workflows/ci.yml
        :alt: CI Status

A quick way to add custom versatile formatting to objects.

* Free software: MIT license
* Python 3.10+ (tested against 3.10, 3.11, 3.12 and 3.13)
* Status: alpha, and never published to PyPI — install from source

Background
----------

This library came out of a Stack Overflow question:
`Hook into the builtin python f-string format machinery to override/extend built-in __format__ methods
<https://stackoverflow.com/questions/55876683/hook-into-the-builtin-python-f-string-format-machinery-to-override-extend-built>`_

The question asked whether custom format specifiers could be applied to *built-in* types, so that you could write
``f"{1:this_specification}"`` without subclassing anything. The short answer is no, not through any supported
mechanism. f-strings do not call ``builtins.format``; the compiler emits a dedicated bytecode instruction, so
monkeypatching ``builtins.format`` has no effect on them::

    >>> import builtins
    >>> builtins.format = lambda *args, **kwargs: 'womp womp'
    >>> format(1, "foo")
    'womp womp'
    >>> f"{1:foo}"
    Traceback (most recent call last):
      ...
    ValueError: Invalid format specifier

The one answer the question received demonstrated that it *is* possible — by rewriting the bytecode of every
module at import time to replace that instruction with a call to a hook function. It is a genuinely clever piece of
work (see `mivdnber/formathack <https://github.com/mivdnber/formathack>`_), and its author was upfront that it was
hacky and likely to break on new Python versions.

It did. The rewrite emits ``ROT_THREE`` and ``CALL_FUNCTION``, both removed in Python 3.11; and the instruction it
searches for, ``FORMAT_VALUE``, no longer exists in Python 3.13, where f-strings compile to ``FORMAT_WITH_SPEC``.

**So this library deliberately does not go down that road.** It restricts itself to classes you control, where
overriding ``__format__`` is ordinary supported Python. Custom specifiers on built-in instances are out of scope,
by choice rather than by omission.

Introduction
------------

f-strings are excellent syntax. But directing an object's formatting to a function like this one:

>>> def format_camel_case(string):
...     """camel cases a sentence"""
...     return ''.join(s.capitalize() for s in string.split())

That normally means overriding ``__format__`` and tying the formatting logic to the class itself.
``simpleformatter`` decouples the two:

>>> from simpleformatter import formattable
>>> @formattable(camcase=format_camel_case)
... class MyStr(str): ...
...
>>> f'{MyStr("lime cordial delicious"):camcase}'
'LimeCordialDelicious'

Library API
-----------

The primary API consists of 3 decorators:

>>> from simpleformatter import formattable, target, formatmethod

``formattable`` decorator
~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``formattable`` decorator to associate a specifier key with a previously defined formatting function:

>>> @formattable(camcase=format_camel_case)
... class MyStr(str): ...
...
>>> f'{MyStr("lime cordial delicious"):camcase}'
'LimeCordialDelicious'

Specifiers registered this way are passed as keyword arguments, so they must be valid Python identifiers. Use
``target`` or ``formatmethod`` to handle the empty specifier.

``target`` decorator
~~~~~~~~~~~~~~~~~~~~

Use the ``target`` decorator to mark a formatting function as the target of one or more specifiers. The decorated
function then serves *any* formattable class:

>>> @target('shout')
... def format_shout(obj, spec):
...     return f'{obj}!!!'.upper()
...
>>> @formattable
... class Greeting(str): ...
...
>>> @formattable
... class Farewell(str): ...
...
>>> f"{Greeting('hello'):shout}"
'HELLO!!!'
>>> f"{Farewell('goodbye'):shout}"
'GOODBYE!!!'

A ``target`` applied with no specifier at all handles the *empty* specifier — plain ``f"{obj}"``. Note that
``target`` registers globally, so doing this affects every formattable class, including inside your own format
methods. It is usually better to scope it to its own ``SimpleFormatter`` instance:

>>> from simpleformatter import SimpleFormatter
>>> sf = SimpleFormatter()
>>> @sf.target
... def default_format(obj):
...     return 'no specifier given'
...
>>> @sf.formattable
... class Plain: ...
...
>>> f"{Plain()}"
'no specifier given'

Each ``SimpleFormatter`` keeps its own registry, so independent sets of specifiers can coexist without colliding.

``formatmethod`` decorator
~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``formatmethod`` decorator makes a method the target of the given specifier(s) *for that class only*:

>>> @formattable
... class Data(float):
...     @formatmethod('Bytes', 'B')
...     def _repr_b_(self):
...         return f'{self} Bytes'
...     @formatmethod('MB')
...     def _repr_mb_(self):
...         return f'{self/1024**2} MB'
...     @formatmethod('GB')
...     def _repr_gb_(self):
...         return f'{self/1024**3} GB'
...
>>> f'{Data(112_113_254):B}'
'112113254.0 Bytes'
>>> f'{Data(112_113_254):MB}'
'106.91953086853027 MB'
>>> f'{Data(112_113_254):GB}'
'0.1044136043637991 GB'

Compound specifiers: numbers with units
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default a specifier has to match the whole format spec. Pass ``suffix=True`` to ``target`` to match the *end* of
the spec instead, which leaves the leading part free to be an ordinary format spec. A suffix target may take a
third argument, which receives that leading part:

>>> length_dict = {'in': 1, 'ft': 1/12, 'cm': 2.54, 'mm': 25.4, 'm': 0.0254}
>>> @target(*length_dict, suffix=True)  # specifiers are: in, ft, cm, mm, m
... def format_convert(value, unit, std_spec):
...     return f'{length_dict[unit] * value:{std_spec}} {unit}'
...
>>> @formattable
... class Measurement(float): ...
...
>>> f'{Measurement(8.45):.3ft}'
'0.704 ft'
>>> f'{Measurement(12):>12.2fmm}'
'      304.80 mm'

The leading part is handed to the standard machinery untouched, so the whole format spec mini-language — fill,
alignment, sign, width, precision and presentation type — is available in front of the unit. When more than one
suffix matches, the longest wins, so ``mm`` beats ``m``.

One gotcha worth knowing: a bare precision like ``.1`` means *one significant digit*, not one decimal place, so
``f'{x:.1ft}'`` produces ``'1e+00 ft'``. If you would rather default to fixed point, do it in the target:

>>> @target(*length_dict, suffix=True)
... def format_fixed(value, unit, std_spec):
...     if std_spec and std_spec[-1] not in 'bcdeEfFgGnosxX%':
...         std_spec += 'f'  # no presentation type given, so default to fixed point
...     return f'{length_dict[unit] * value:{std_spec}} {unit}'
...
>>> @formattable
... class Length(float): ...
...
>>> f'{Length(12):.1ft}'
'1.0 ft'
>>> f'{Length(12):.2cm}'
'30.48 cm'
>>> f'{Length(12):.3m}'
'0.305 m'

Resolution order
~~~~~~~~~~~~~~~~

When more than one of the above could handle a specifier, they are tried in this order:

1. a ``formatmethod`` declared with ``override=True``
2. an *exact* specifier registered on the class via ``formattable``
3. an *exact* specifier registered globally via ``target``
4. the longest *suffix* specifier registered via ``target(..., suffix=True)``
5. a ``formatmethod`` without ``override``
6. the class's original ``__format__``

Step 6 means built-in specifiers keep working on a decorated class — unrecognized specifiers are handed back to the
original machinery rather than raising:

>>> @formattable
... class Length(float): ...
...
>>> f"{Length(8.45):.2f}"
'8.45'

Limitations
-----------

**Built-in types are not supported**, and cannot be without bytecode manipulation — see Background above.

**Suffix specifiers can shadow the built-in presentation types.** Matching is done on the raw spec text, so a
suffix that collides with one of ``b c d e E f F g G n o s x X %`` will capture ordinary format specs — registering
``f`` as a suffix would swallow ``.2f``. Multi-character unit names do not run into this.

**Suffix matching is only available on** ``target``. ``formatmethod`` and the ``formattable`` keyword arguments
still match the whole spec exactly.

Development
-----------

Install in editable mode with the test dependencies, then run the suite::

    $ pip install -e ".[dev]"
    $ pytest

``pytest`` runs both the unit tests and the module doctests. To run against every supported interpreter::

    $ tox

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

Thanks to `mivdnber <https://github.com/mivdnber>`_ for the Stack Overflow answer that settled the built-in types
question.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
