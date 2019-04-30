# -*- coding: utf-8 -*-

"""primary api decorators

The api decorators are formattable, method, and function

Examples:

    >>> @target("spec_f1", "spec_f2")
    >>> def fmtr(): ...

    >>> @formattable
    >>> class A: ...

    >>> @formattable
    >>> class B: ...
    >>>     @formatmethod("spec_m1", "spec_m2")
    >>>     def fmtr(self): ...

    >>> f"{A():spec_f1}"
    >>> f"{A():spec_f2}"
    >>> f"{B():spec_m1}"
    >>> f"{B():spec_m2}"
    >>> f"{B():spec_f1}"
    >>> f"{B():spec_f2}"
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
