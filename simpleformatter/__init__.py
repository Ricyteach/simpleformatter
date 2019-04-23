# -*- coding: utf-8 -*-

"""primary api decorators

The api decorators are formattable, method, and function

Examples:

    >>> @function("spec_f1", "spec_f2")
    >>> def fmtr(): ...

    >>> @formattable
    >>> class A: ...

    >>> @formattable
    >>> class B: ...
    >>>     @method("spec_m1", "spec_m2")
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

from .simpleformatter import SimpleFormatter

simpleformatter = SimpleFormatter()
formattable = simpleformatter.formattable
method = simpleformatter.method
function = simpleformatter.function

# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())
