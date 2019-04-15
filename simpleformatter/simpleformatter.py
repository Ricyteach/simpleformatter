# -*- coding: utf-8 -*-

"""Main module."""
from inspect import signature

# re-create object.__format__ error message
default_type_error_msg = "unsupported format string passed to {cls.__qualname__}.__format__"

empty_str = ""  # for readability


def simpleformatter(func=None, *, spec=None):
    """Decorator for registering formatter specs with formatter functions"""
    if func is not None and not callable(func):
        raise TypeError(f"{func.__qualname__!r} func not a callable; spec must be keyword argument")

    if spec is None:
        spec=empty_str

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

    def __format__(self, format_spec=""):
        try:
            # get registered formatter
            formatter = self.__lookup_formatter(format_spec)
        except SimpleFormatterError as e1:
            try:
                # format_spec not registered with a formatter; fall back on parent __format__ functionality
                return super().__format__(format_spec)
            except Exception as e2:
                # if parent functionality fails, raise from previous exception for clarity
                raise e2 from e1
        else:
            # user defined simpleformatter function *may* discard format_spec argument for convenience (DRY!)
            if len(signature(formatter).parameters) == 1:
                return formatter(self)
            return formatter(self, format_spec)

    @classmethod
    def __lookup_formatter(cls, format_spec):
        """Gets the registered formatting function, raises SimpleFormatterError if one isn't found"""
        for cls_obj in cls.__mro__:
            try:
                return cls.__subclass_dict[cls_obj][format_spec]
            except KeyError:
                continue
        else:
            raise SimpleFormatterError(f"{format_spec!r} format_spec not registered for {cls.__qualname__} class")

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