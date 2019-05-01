from __future__ import annotations

from inspect import signature
from itertools import repeat
from string import Formatter
from typing import Optional, NewType, Callable, Dict, Mapping, Generic, TypeVar, Type, Union

SPECS = "specs"  # formatmethod specifiers holder attribute name
DEFAULT_DUNDER_FORMAT = "_default__format__"  # attr name to keep reference to original __format__
FORMATTERS = "_formatters"  # attr name to keep reference to applied simpleformatter instances
OVERRIDE = "override"  # attr name to specify if a formatmethod should override a formatter target

TSimpleFormatter = TypeVar("TSimpleFormatter", bound="SimpleFormatter")
T = TypeVar("T")
Spec = NewType("Spec", str)
ResultStr = NewType("ResultStr", str)
Target = Union[Callable[[T, Spec], ResultStr], Callable[[T], ResultStr], Callable[[], ResultStr]]
BoundTarget = Union[Callable[[Spec], ResultStr], Callable[[], ResultStr]]
FormatRegister = Dict[Spec, Target]
x: Target = lambda a, b, c, d: ResultStr("1")


def _new__format__(obj: T, format_spec: Spec):
    """Replacement __format__ formatmethod for formattable classes"""
    fmtr: Formatter
    for fmtr in reversed(getattr(obj, FORMATTERS, ())):
        try:
            return fmtr.format_field(obj, format_spec)
        except SimpleFormatterError:
            pass
    else:
        try:
            target = getattr(obj, DEFAULT_DUNDER_FORMAT)
        except AttributeError:
            raise ValueError("invalid format specifier")
        else:
            return target(format_spec)


class SimpleFormatterError(Exception):
    pass


class formatmethod(Generic[T]):
    """Create a formatmethod. Accessed by specific format specifiers and returns a formatted version of the string."""

    def __init__(self, method: Optional[Target] = None, *specs: Spec, override: bool = False) -> None:
        setattr(self, SPECS, specs if specs else ("",))

        # TODO: implement override
        if method is not None:
            self(method.__func__ if hasattr(method, "__func__") else method)

    def __get__(self, instance, owner) -> Union[formatmethod, BoundTarget]:
        if instance is not None:
            return self.__func__.__get__(instance, owner)
        return self

    def __call__(self, method: Target) -> formatmethod:
        self._method = method
        return self

    @property
    def __func__(self) -> Target:
        return self._method


class SimpleFormatter(Formatter, Generic[T]):

    target_reg: FormatRegister
    cls_reg: Dict[Type[T], FormatRegister]

    def __init__(self) -> None:
        self.target_reg = dict()
        self.cls_reg = dict()

    def formattable(self, cls: Optional[Type[T]] = None, *, target_dict: Optional[Mapping[Spec, Target]] = None,
                    **target_kwargs: Target) -> Type[T]:

        def decorator(c: Type[T]) -> Type[T]:
            self.register_cls(c, target_dict, **target_kwargs)
            return c

        return decorator if cls is None else decorator(cls)

    def target(self, func: Optional[Union[Target, Spec]] = None, *specs: Spec) -> Target:

        if isinstance(func, str):
            func, specs = None, (func, *specs)

        def decorator(f: Target) -> Target:
            self.register_target(f, *specs)
            return f

        return decorator if func is None else decorator(func)

    def format_field(self, value: T, format_spec: Spec) -> ResultStr:
        handler = self.spec_handler(value, format_spec)
        # user defined targets *may* discard arguments for convenience
        # TODO: figure out if want to allow discarding self and keeping format_spec? how to do? check staticmethod??
        if len(signature(handler).parameters) == 0:
            return handler()
        if len(signature(handler).parameters) == 1:
            return handler(value)
        return handler(value, format_spec)

    def spec_handler(self, obj: T, format_spec: Spec) -> Target:
        """Retrieve the handling target given an object and format_spec"""
        # formattable decorator first
        try:
            return self.lookup_cls_target(obj, format_spec)
        except SimpleFormatterError:
            pass
        # formatmethod decorators second
        try:
            return self.lookup_formatmethod(obj, format_spec)
        except SimpleFormatterError:
            pass
        # target decorators third
        try:
            return self.lookup_gen_target(format_spec)
        except SimpleFormatterError:
            pass
        # signal spec handling failure
        raise SimpleFormatterError(f"unhandled format_spec: {format_spec!r}")

    @staticmethod
    def lookup_formatmethod(obj: T, format_spec: Spec) -> Target:
        try:
            # TODO: swap out `member` below for the formatmethod
            *_, m_name = (attr for attr, member in ((attr, getattr(obj, attr)) for attr in dir(obj))
                          if format_spec in getattr(member, SPECS, ()))
        except ValueError:
            raise SimpleFormatterError()
        return getattr(obj, m_name)

    def lookup_cls_target(self: SimpleFormatter, obj: T, format_spec: Spec) -> Target:
        try:
            return self.cls_reg[type(obj)][format_spec]
        except KeyError:
            raise SimpleFormatterError(f"no class-level target for spec: {format_spec!r}")

    def lookup_gen_target(self: SimpleFormatter, format_spec: Spec) -> Target:
        try:
            return self.target_reg[format_spec]
        except KeyError:
            raise SimpleFormatterError(f"no target for spec: {format_spec!r}")

    def register_cls(self, cls: Type[T], target_dict: Optional[Mapping[Spec, Target]] = None,
                     **target_kwargs: Target) -> None:
        setattr(cls, DEFAULT_DUNDER_FORMAT, getattr(cls, DEFAULT_DUNDER_FORMAT, cls.__format__))
        cls.__format__ = _new__format__
        self.cls_reg[cls] = dict()
        if target_dict is None:
            target_dict = {}
        self.cls_reg[cls].update(target_dict, **target_kwargs)
        try:
            getattr(cls, FORMATTERS).append(self)
        except AttributeError:
            setattr(cls, FORMATTERS, [self])

    def register_target(self, target: Target, *specs: Spec) -> None:
        self.target_reg.update(zip(specs, repeat(target)))
