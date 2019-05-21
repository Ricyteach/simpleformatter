===============
simpleformatter
===============


.. image:: https://img.shields.io/pypi/v/simpleformatter.svg
        :target: https://pypi.python.org/pypi/simpleformatter

.. image:: https://img.shields.io/travis/Ricyteach/simpleformatter.svg
        :target: https://travis-ci.org/Ricyteach/simpleformatter

.. image:: https://readthedocs.org/projects/simpleformatter/badge/?version=latest
        :target: https://simpleformatter.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

A quick way to add custom versatile formatting to objects


* Free software: MIT license
* Documentation: https://simpleformatter.readthedocs.io.

Introduction
-------------

f-strings are taking over the python world. But it requires a lot of effort to take a function like this:

>>> def format_camel_case(string):
...     """camel cases a sentence"""
...     return ''.join(s.capitalize() for s in string.split())
...

...and direct the formatting of a user object to that function by customizing the f-string syntax:

>>> my_phrase = MyString("lime cordial delicious")
>>> f"{my_phrase:camcase}"
'LimeCordialDelicious'

...or, perhaps use f-strings to send measurements to a unit conversion formatting function:

>>> x = Measurement(12, 'inches')
>>> f'{x:.1ft}'
'1.0 ft'
>>> f'{x:.2cm}'
'30.48 cm'
>>> f'{x:.3m}'
'0.305 m'

Implementing these examples requires overriding the `__format__` method, and including all the formatting logic tied up as part of the class. What a bummer. `simpleformatter` provides a better way.

Library API
-----------

The primary API consists of 3 decorators:

>>> from simpleformatter import formattable, target, formatmethod

`formattable` decorator
~~~~~~~~~~~~~~~~~~~~~~~

Use the `formattable` decorator to associate a specifier key with a previously defined formatting function:

>>> @formattable(camcase=format_camel_case)
... class MyStr(str): ...
...
>>> f'{MyStr("lime cordial delicious"):camcase}'
'LimeCordialDelicious'

`target` decorator
~~~~~~~~~~~~~~~~~~~~~~~

Use the `target` decorator to mark a formatting function as a formatting specifier(s) target:

>>> length_dict = {'in': 1, 'ft': 1/12, 'cm': 2.54, 'mm': 25.4, 'm': 0.0254}
>>> def convert(value, unit):
...     return length_dict[unit] * value
...
>>> import itertools as it
>>> @target(*length_dict)  # specifiers are: in, ft, cm, mm, m
... def format_convert(value, unit_spec):
...     unit = ''.join(reversed(list(it.takewhile(lambda x: x.isalpha(), reversed(unit_spec)))))
...     return f'{convert(value, unit):{unit_spec[:-len(unit)]}} {unit}'
...

Now the decorated formatting function will act as a target for any decorated user class:

>>> @formattable
... class Diameter(float): ...
...
>>> @formattable
... class Depth(float): ...
...
>>> format_convert(Diameter(8.45), ".3ft")
'0.704 ft'
>>> format_convert(3.77, ".4mm")
'95.76 mm'

`formatmethod` decorator
~~~~~~~~~~~~~~~~~~~~~~~~

The `formatmethod` decorator makes the method a target of the formatting specifier(s) *for that class only*:

>>> @formattable
... class Data(float):
...     @formatmethod('', 'B')
...     def _repr_b_(self):
...         return f'{self} B'
...     @formatmethod('KB')
...     def _repr_kb_(self):
...         return f'{self/1024} KB'
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

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
