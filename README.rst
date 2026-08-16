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

>>> length_dict = {'in': 1, 'ft': 1/12, 'cm': 2.54, 'mm': 25.4, 'm': 0.0254}
>>> @target(*length_dict)  # specifiers are: in, ft, cm, mm, m
... def format_convert(value, unit):
...     return f'{length_dict[unit] * value:.4g} {unit}'
...
>>> @formattable
... class Diameter(float): ...
...
>>> @formattable
... class Depth(float): ...
...
>>> f"{Diameter(8.45):ft}"
'0.7042 ft'
>>> f"{Depth(3.77):mm}"
'95.76 mm'

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

Resolution order
~~~~~~~~~~~~~~~~

When more than one of the above could handle a specifier, they are tried in this order:

1. a ``formatmethod`` declared with ``override=True``
2. a specifier registered on the class via ``formattable``
3. a specifier registered globally via ``target``
4. a ``formatmethod`` without ``override``
5. the class's original ``__format__``

Step 5 means built-in specifiers keep working on a decorated class — unrecognized specifiers are handed back to the
original machinery rather than raising:

>>> @formattable
... class Length(float): ...
...
>>> f"{Length(8.45):.2f}"
'8.45'

Limitations
-----------

**Specifiers are matched exactly.** There is no parsing of compound specifiers, so a registered ``ft`` target does
not match the specifier ``.3ft``; that falls through to ``float.__format__`` and raises ``ValueError``. Supporting
something like ``f"{x:.3ft}"`` would require deciding how a specifier is split into a "standard" part and a custom
part, and how ambiguity between competing targets is resolved. That design work has not been done.

**Built-in types are not supported**, and cannot be without bytecode manipulation — see Background above.

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
