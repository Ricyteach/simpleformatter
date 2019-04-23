# -*- coding: utf-8 -*-

"""Top-level package for simpleformatter."""

__author__ = """Ricky L Teachey Jr"""
__email__ = 'ricky@teachey.org'
__version__ = '0.1.0'

from .simpleformatter import formattable, method, function

# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())
