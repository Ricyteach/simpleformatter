# -*- coding: utf-8 -*-

"""Main module."""
import functools
from inspect import signature
from copy import deepcopy

# re-create object.__format__ error message
default_type_error_msg = "unsupported format string passed to {cls.__qualname__}.__format__"

empty_str = ""  # for readability
SPECS_HOLDER_ATTR = "_simpleformatter_specs"  # might change this later?
SPECS_REG_DICT = "_simpleformatter_registry"


class NoArgType:
    def __repr__(self):
        return "NO_ARG"


NO_ARG = NoArgType()


def _negotiate_decorator(dec, pos1):
    """Determine if the decorator was called with or without a first arg when it was invoked and act accordingly"""

    if pos1 is NO_ARG:
        return dec
    return dec(pos1)


def _add_registry(cls, reg):
    """Attach a formatter registry to the class object"""
    setattr(cls, SPECS_REG_DICT, reg)


def _get_registry(cls):
    """Retrieve the formatter registry from the class object; raise SimpleFormatterError when not found"""
    try:
        return getattr(cls, SPECS_REG_DICT)
    except AttributeError as e:
        raise SimpleFormatterError(f"{cls.__qualname__} class has no {SPECS_REG_DICT} registry") from e


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
            # TODO: figure out if want to allow discarding self and keeping format_spec? how to do? check staticmethod??
            if len(signature(formatter).parameters) == 1:
                return formatter(self)
            return formatter(self, format_spec)

    cls.__format__, cls._default__format__ = deepcopy(_new__format__), deepcopy(cls.__format__)


def _lookup_formatter(cls, format_spec):
    """Gets the corresponding formatting function, raises SimpleFormatterError if one isn't found"""

    for cls_obj in cls.__mro__:
        try:
            return _get_registry(cls_obj)[format_spec]
        except KeyError:
            continue

    raise SimpleFormatterError(f"no {format_spec!r} format_spec found for {cls.__qualname__} class")


def _register_all_formatters(cls):
    """Register the formatting functions marked in the class __dict__"""

    formatter_dict = dict()

    # traverse in forward order so most recently defined formatter is registered for each spec
    for member in vars(cls).values():
        for format_spec in getattr(member, SPECS_HOLDER_ATTR, ()):
            formatter_dict.update({format_spec: member})

    try:
        _register_formatters(cls, formatter_dict)
    except SimpleFormatterError as e:
        raise SimpleFormatterError("formatter registration failed due to no formatter registry") from e


def _register_formatters(cls, formatter_dict):
    """Register the spec with its formatting function and place in class registry"""
    _get_registry(cls).update(formatter_dict)


def _class_decorator(pos1, formatter_dict):
    """Private decorator for adding customized __format__ method and formatter registry to class."""
    # TODO: implement spec/formatter handling on the class level:
    #   @simpleformatter(spec="spec", func=spec_handler)
    #   class C: ...

    def wrap_cls__format__(cls):
        _add_registry(cls, formatter_dict)
        _register_all_formatters(cls)
        _wrap_cls__format__(cls)
        return cls

    return _negotiate_decorator(wrap_cls__format__, pos1)


def _formatter_func_decorator(pos1, specs):
    """Private decorator for attaching specs to formatter functions"""

    # spec assumed to be only empty_str when empty
    if not specs:
        specs = {empty_str}

    try:
        iter_specs = iter(specs)
    except TypeError as e:
        raise SimpleFormatterError("specs must be iterable") from e

    try:
        specs_set = {*iter_specs}
    except TypeError as e:
        raise SimpleFormatterError("specs must be hashable") from e

    # internal decorator
    def mark_simpleformatter_spec(func):
        try:
            s = getattr(func, SPECS_HOLDER_ATTR)
        except AttributeError:
            setattr(func, SPECS_HOLDER_ATTR, specs_set)
        else:
            s.update(specs_set)
        return func

    return _negotiate_decorator(mark_simpleformatter_spec, pos1)


def simpleformatter(pos1=NO_ARG, *specs, formatter_dict=None, **formatter_kwargs):
    """simpleformatter api decorator"""

    if pos1 is not NO_ARG and isinstance(pos1, str):
        # relocate first argument to specs when it is a spec string
        # this assumes decorator was applied like:
        #
        #    @simpleformatter.simpleformatter("spec1", "spec2")
        #    def format_handler(self): ...
        to_decorate, specs = NO_ARG, (pos1, *specs)
    else:
        # first argument is either a class or function/method
        to_decorate = pos1

    def api_decorator(cls_or_func):
        """Actual decorator; cls_or_func is either a class or function/method"""

        nonlocal formatter_dict, specs, formatter_kwargs

        if isinstance(cls_or_func, type):
            # decorator being applied to a class
            if specs:
                raise SimpleFormatterError("specs arguments should only be used when decorating a function")
            if formatter_dict is None:
                formatter_dict = dict(**formatter_kwargs)
            else:
                formatter_dict.update(**formatter_kwargs)
            return _class_decorator(cls_or_func, formatter_dict)

        # assume decorator attempting to be applied to a function/method
        if not callable(cls_or_func):
            msg = f"{cls_or_func!r} not a callable" + \
                  ("; spec must be keyword argument" if isinstance(cls_or_func, str) else "")
            raise TypeError(msg)

        if formatter_kwargs:
            raise SimpleFormatterError("formatter_kwargs arguments should only be used when decorating the class")
        if formatter_dict is not None:
            raise SimpleFormatterError("formatter_dict argument should only be used when decorating the class")
        return _formatter_func_decorator(cls_or_func, specs)

    return _negotiate_decorator(api_decorator, to_decorate)


class SimpleFormatterError(Exception):
    """I'm an exception. Kneel before me. Lower."""
    pass
