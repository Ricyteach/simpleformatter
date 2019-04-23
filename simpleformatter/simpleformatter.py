# -*- coding: utf-8 -*-

"""Main module."""
import functools
from inspect import signature
from copy import deepcopy

from itertools import repeat

# # re-create object.__format__ error message
# default_type_error_msg = "unsupported format string passed to {cls.__qualname__}.__format__"

empty_str = ""  # for readability
GEN_SPECS_ATTR = "_simpleformatter_general_specs"  # formatting function attribute holding a set of specs that use it
METH_SPECS_ATTR = "_simpleformatter_method_specs"  # formatting function attribute holding a set of specs that use it
CLS_REG_ATTR = "_simpleformatter_registry"  # formattable class attr holding registry
GEN_REG = dict()  # general registry holds spec: function pairs applicable to general scope (all formattable types)


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
    try:
        setattr(cls, CLS_REG_ATTR, reg)
    except TypeError as e:
        import builtins
        if cls in vars(builtins).values():
            raise TypeError(f"the {cls!s} builtin cannot be modified with simpleformatter functionality") from e
        raise e


def _get_cls_registry(cls):
    """Retrieve the formatter registry from the class object; raise SimpleFormatterError when not found"""
    try:
        return getattr(cls, CLS_REG_ATTR)
    except AttributeError as e:
        raise SimpleFormatterError(f"{cls.__qualname__} class has no {CLS_REG_ATTR} registry") from e


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


def _lookup_cls_formatter(cls, format_spec):
    """Gets the corresponding class formatting function, raises SimpleFormatterError if one isn't found"""

    for cls_obj in cls.__mro__:
        try:
            return _get_cls_registry(cls_obj)[format_spec]
        except KeyError:
            continue

    raise SimpleFormatterError(f"no {format_spec!r} format_spec found for {cls.__qualname__} class")


def _lookup_general_formatter(format_spec):
    """Gets the corresponding general formatting function, raises SimpleFormatterError if one isn't found"""
    try:
        return GEN_REG[format_spec]
    except KeyError:
        raise SimpleFormatterError(f"no {format_spec!r} format_spec found in general registry")


def _lookup_formatter(cls, format_spec):
    """Gets the corresponding formatting function, raises SimpleFormatterError if one isn't found"""
    try:
        return _lookup_cls_formatter(cls, format_spec)
    except SimpleFormatterError as e1:
        try:
            return _lookup_general_formatter(format_spec)
        except SimpleFormatterError as e2:
            raise SimpleFormatterError(f"no {format_spec!r} format_spec found")


def _register_all_formatters(cls):
    """Register the formatting functions marked in the class __dict__"""

    formatter_dict = dict()

    # traverse in forward order so most recently defined formatter is registered for each spec
    for member in vars(cls).values():
        for format_spec in getattr(member, METH_SPECS_ATTR, ()):
            formatter_dict.update({format_spec: member})

    reg = _get_cls_registry(cls)
    _register_formatters(formatter_dict, reg)


def _register_formatters(formatter_dict, registry):
    """Register the spec with its formatting function and place in class registry"""

    if not all(isinstance(k, str) for k in formatter_dict.keys()):
        # specs must be strings
        raise TypeError(f"{next(s for s in formatter_dict.keys() if not isinstance(s, str))!r} spec is not a str")

    registry.update(formatter_dict)


def _class_decorator(pos1, formatter_dict):
    """Private decorator for adding customized __format__ method and formatter registry to class."""
    # TODO: implement spec/formatter handling on the class level:
    #   @simpleformatter(spec="spec", func=spec_handler)
    #   class C: ...

    def wrap_cls__format__(cls):
        _add_registry(cls, formatter_dict)
        _register_all_formatters(cls)
        _check_for_general_formatters(cls)
        _wrap_cls__format__(cls)
        return cls

    return _negotiate_decorator(wrap_cls__format__, pos1)


def _check_for_general_formatters(cls):
    """check to see if any class methods erroneously decorated by @general instead of @method"""
    if any(hasattr(member, GEN_SPECS_ATTR) for member in vars(cls).values()):
        raise SimpleFormatterError(f"the function decorator should never be used on methods like "
                                   f"{next(member for member in dict(cls).values() if hasattr(member, GEN_SPECS_ATTR))}")


def _mark_formatter(func, specs_attr, *specs):
    """Attach specs to a formatter function"""

    # spec assumed to be only empty_str when empty
    try:
        specs_set = set(specs if specs else (empty_str,))
    except TypeError as e:
        raise SimpleFormatterError("specs must be hashable") from e

    try:
        func_spec_set = getattr(func, specs_attr)
    except AttributeError:
        setattr(func, specs_attr, specs_set)
    else:
        func_spec_set.update(specs_set)


def _handle_decorator_args(check_type, *args):
    """Figure out how the decorator was applied and return appropriate arguments tuple in form of:

        thing to be decorated, arg1, arg2, etc.

    the thing to be decorated will be NO_ARG if it wasn't yet supplied to the decorator as an argument
    """
    if not isinstance(check_type, type):
        raise SimpleFormatterError("decorator handling failed- check_type must be a type")

    to_decorate = NO_ARG

    try:
        # extract first argument to test if it is a spec string
        pos1, *args = args
    except ValueError:
        # assume decorator was applied with no positional arguments like:
        #
        #    @decorator()
        #
        to_decorate = NO_ARG
    else:
        if isinstance(pos1, check_type):
            # assume decorator was applied like:
            #
            #    @decorator(check_type_inst1[, type_inst])
            #
            args = (pos1, *args)
        else:
            # assume first argument is NOT a check_type_inst, e.g.:
            #
            #    @decorator
            #    class OtherType: ...
            #
            # or:
            #
            #    @decorator
            #    def func(): ...
            #
            to_decorate = pos1

    return (to_decorate, *args)


def _callable_decorator(*specs, callable_registry=None):
    """Private decorator for all functions (methods and non-methods)"""

    # determine how api decorator *args were supplied (to_decorate may be NO_ARGS)
    to_decorate, *specs = _handle_decorator_args(str, *specs)

    def decorator_inner(func):
        """Actual decorator; meth is a function (method and non-method)"""

        nonlocal specs, callable_registry

        if not callable(func):
            raise TypeError(f"{func!r} not a callable")
        if callable_registry is not None:
            _mark_formatter(func, GEN_SPECS_ATTR, *specs)
            # register general function formatters only, method registration occurs during @formattable decoration
            _register_formatters(dict(zip(specs, repeat(func))), callable_registry)
        else:
            _mark_formatter(func, METH_SPECS_ATTR, *specs)
        return func

    return _negotiate_decorator(decorator_inner, to_decorate)


"""api decorators

The api decorators are formattable, method, and function

Examples:

    @function("spec_f1", "spec_f2")
    def fmtr(): ...
    
    @formattable
    class A: ...
    
    @formattable
    class B: ...
      @method("spec_m1", "spec_m2")
      def fmtr(): ...
    
    >>> f"{A():spec_f1}"
    >>> f"{A():spec_f2}"
    >>> f"{B():spec_m1}"
    >>> f"{B():spec_m2}"
    >>> f"{B():spec_f1}"
    >>> f"{B():spec_f2}"
"""


def function(*specs):
    """simpleformatter api decorator for non-method functions

    raises SimpleFormatterError if applied to a formattable class method (use function decorated instead)
    """

    # non-method functions are tracked in the general registry
    return _callable_decorator(*specs, callable_registry=GEN_REG)


def method(*specs, cls=None):
    """simpleformatter api decorator for methods of formattable classes; monkey patched methods must specify the cls"""

    # the method's class cannot be known at runtime so we will track method functions in their rspective class
    # registries (ie, not callable_registry kwarg supplied to _callable_decorator)
    return _callable_decorator(*specs)


def formattable(cls=NO_ARG, *, formatter_dict=None, **formatter_kwargs):
    """simpleformatter api decorator for classes"""

    # in case someone erroneously puts the formatter_dict as positional argument
    if not isinstance(cls, (type, NoArgType)):
        raise TypeError(f"cls not a type; decorator erroneously applied to a {cls.__qualname__} object")

    def api_decorator(cls_arg):
        """Actual decorator; cls_arg is a type"""

        nonlocal formatter_dict, formatter_kwargs

        if not isinstance(cls_arg, type):
            raise SimpleFormatterError(f"{formattable.__name__} decorator should only be used when decorating a class")

        if formatter_dict is None:
            formatter_dict = dict(**formatter_kwargs)
        else:
            formatter_dict.update(**formatter_kwargs)
        return _class_decorator(cls_arg, formatter_dict)

    return _negotiate_decorator(api_decorator, cls)


class SimpleFormatterError(Exception):
    """I'm an exception. Kneel before me. Lower."""
    pass
