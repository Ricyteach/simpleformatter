# -*- coding: utf-8 -*-

"""Main module."""
import functools
from inspect import signature
from copy import deepcopy

# re-create object.__format__ error message
default_type_error_msg = "unsupported format string passed to {cls.__qualname__}.__format__"

empty_str = ""  # for readability
SPECS_HOLDER_ATTR = "_simpleformatter_specs"  # might change this later?


class NoArgType:
    def __repr__(self):
        return "NO_ARG"


NO_ARG = NoArgType()


def _negotiate_decorator(dec, pos1):
    """Determine if the decorator was called and act accordingly"""

    if pos1 is NO_ARG:
        return dec
    return dec(pos1)


def _wrap_cls__format__(cls):
    """Private function to decorate cls.__format__ function"""

    @functools.wraps(cls.__format__)
    def _new__format__(self, format_spec=""):
        """Wrapper for the cls.__format__ method; falls back on default behavior when no formatter found"""

        try:
            formatter = _lookup_formatter(cls, format_spec)
        except SimpleFormatterError as e1:
            try:
                # formatter not found for format_spec; attempt fall back on default __format__ functionality
                return cls._default__format__(self, format_spec)
            except Exception as e2:
                # if default functionality fails, raise from previous exception for clarity
                raise e2 from e1
        else:
            # user defined simpleformatter function *may* discard arguments for convenience (staticmethod)
            if len(signature(formatter).parameters) == 0:
                return formatter()
            # user defined simpleformatter function *may* discard format_spec argument for convenience (DRY!)
            # TODO: figure out if want to allow discarding self and keeping format_spec? how to do?
            if len(signature(formatter).parameters) == 1:
                return formatter(self)
            return formatter(self, format_spec)

    cls.__format__, cls._default__format__ = deepcopy(_new__format__), deepcopy(cls.__format__)


def _lookup_formatter(cls, format_spec):
    """Gets the corresponding formatting function, raises SimpleFormatterError if one isn't found"""

    for cls_obj in cls.__mro__:
        # traverse in reverse order to get most recently defined formatter for that spec
        for member in reversed(list(vars(cls_obj).values())):
            if format_spec in getattr(member, SPECS_HOLDER_ATTR, ()):
                return member
    else:
        raise SimpleFormatterError(f"{format_spec!r} format_spec not registered for {cls.__qualname__} class")


def _class_decorator(cls_arg=NO_ARG, *, spec=None, func=None):
    """Private decorator for adding customized __format__ method to class."""

    def wrap_cls__format__(cls_obj):
        _wrap_cls__format__(cls_obj)
        return cls_obj

    return _negotiate_decorator(wrap_cls__format__, cls_arg)


def _formatter_func_decorator(func=NO_ARG, *, spec=None):
    """Private decorator for registering formatter specs with formatter functions"""

    if spec is None:
        spec = empty_str

    def mark_simpleformatter_spec(f):
        try:
            specs_set = getattr(f, SPECS_HOLDER_ATTR)
        except AttributeError:
            try:
                specs_set = {spec}
            except TypeError as e:
                raise SimpleFormatterError("spec must be hashable") from e
            else:
                setattr(f, SPECS_HOLDER_ATTR, specs_set)
        else:
            specs_set.add(spec)
        return f

    return _negotiate_decorator(mark_simpleformatter_spec, func)


def simpleformatter(pos1=NO_ARG, *, spec=None, func=None):
    """simpleformatter api decorator"""

    # arguments to apply to final returned decorator function
    dec_kwargs = dict()

    def api_decorator(cls_or_func):
        """Actual decorator; cls_or_func is either a class or function/method"""
        if isinstance(cls_or_func, type):
            # decorator being applied to a class
            dec_kwargs.update(spec=spec, func=func)
            return _class_decorator(cls_or_func, **dec_kwargs)

        # assume decorator attempting to be applied to a function/method
        if not callable(cls_or_func):
            msg = f"{cls_or_func!r} not a callable" + \
                  ("; spec must be keyword argument" if isinstance(cls_or_func, str) else "")
            raise TypeError(msg)

        if func is not None:
            raise SimpleFormatterError("func argument should only be used when decorating the class")
        dec_kwargs.update(spec=spec)
        return _formatter_func_decorator(cls_or_func, **dec_kwargs)

    return _negotiate_decorator(api_decorator, pos1)


class SimpleFormatterError(Exception):
    pass
