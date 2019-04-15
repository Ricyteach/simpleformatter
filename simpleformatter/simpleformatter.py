# -*- coding: utf-8 -*-

"""Main module."""
from string import Formatter

OVERRIDE_OBJECT = True


def override_object(val):
    """Set flag for overriding the default capability of object.__format__ to handle these:

        >>> format(obj)
        >>> format(obj, "")
        >>> f'{obj}'
        >>> f'{obj:}'
        """
    if val not in (True, False):
        raise SimpleFormatterError("object.__format__ override must be True or False")
    global OVERRIDE_OBJECT
    OVERRIDE_OBJECT = val


def simpleformatter(func=None, *, spec=None):
    """Decorator for registering formatter specs with formatter functions"""
    if func is not None and not callable(func):
        raise TypeError(f"{func.__qualname__!r} func not a callable; spec must be keyword argument")

    def mark_simpleformatter_spec(f):
        try:
            specs_set = f._simpleformatter_specs
        except AttributeError:
            try:
                f._simpleformatter_specs = {spec}
            except TypeError as e:
                raise SimpleFormatterError("spec must be a valid dict key") from e
        else:
            specs_set.add(spec)
        return f

    if func is None:
        return mark_simpleformatter_spec
    else:
        return mark_simpleformatter_spec(func)


class SimpleFormattable:
    __subclass_dict = dict()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__register_marked()

    def __format__(self, format_spec):
        cls=type(self)
        try:
            formatter_cls_dict = self.__subclass_dict[cls]
        except KeyError as e:
            raise SimpleFormatterError(f"{cls.__qualname__} class not registered in SimpleFormattable.__subclass_dict") from e
        try:
            formatter = formatter_cls_dict[format_spec]
        except KeyError:
            return super().__format__(format_spec)
        else:
            try:
                return formatter(self, format_spec)
            except TypeError:
                # formatter function may discard format_spec argument
                return formatter(self)

    @classmethod
    def __register(cls, spec, func):
        cls.__subclass_dict[cls][spec] = func

    @classmethod
    def __register_marked(cls):
        if cls not in cls.__subclass_dict:
            cls.__subclass_dict[cls]=dict()
        for member in vars(cls).values():
            if callable(member) and hasattr(member, "_simpleformatter_specs"):
                for spec in member._simpleformatter_specs:
                  cls.__subclass_dict[cls][spec] = member


class SimpleFormatterError(Exception):
    pass