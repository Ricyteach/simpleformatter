# -*- coding: utf-8 -*-

"""primary api decorators

The api decorators are formattable, formatmethod, and target

Examples:

>>> @target("spec_f1", "spec_f2")
... def fmtr_func():
...     return "fmtr_func"
...
>>> @formattable
... class A: ...
...
>>> @formattable
... class B:
...     @formatmethod("spec_m1", "spec_m2")
...     def fmtr_method(self):
...         return "fmtr_method"
...
>>> f"{A():spec_f1}"
'fmtr_func'
>>> f"{A():spec_f2}"
'fmtr_func'
>>> f"{B():spec_m1}"
'fmtr_method'
>>> f"{B():spec_m2}"
'fmtr_method'
>>> f"{B():spec_f1}"
'fmtr_func'
>>> f"{B():spec_f2}"
'fmtr_func'
"""


__author__ = """Ricky L Teachey Jr"""
__email__ = 'ricky@teachey.org'
__version__ = '0.1.0'

from .simpleformatter import SimpleFormatter, formatmethod

simpleformatter = SimpleFormatter()
formattable = simpleformatter.formattable
target = simpleformatter.target

# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())
