from __future__ import annotations

from inspect import signature
from itertools import repeat
from string import Formatter
from typing import Optional, NewType, Callable, Dict, Mapping, Generic, TypeVar, Type, Union, Sequence

SPECS = "specifiers"  # formatmethod specifiers holder attribute name
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


class SimpleFormatterError(Exception):
    pass


def _new__format__(obj: T, format_spec: Spec) -> ResultStr:
    """Replacement __format__ formatmethod for formattable classes"""

    target: Target
    try:
        target = compute_formatting_func(obj, format_spec)
    except SimpleFormatterError:
        try:
            target = getattr(obj, DEFAULT_DUNDER_FORMAT)
        except AttributeError:
            raise ValueError("invalid format specifier")

    # user defined targets *may* discard arguments for convenience
    # TODO: figure out if want to allow discarding self and keeping format_spec? how to do? check staticmethod??
    if len(signature(target).parameters) == 0:
        return target()
    if len(signature(target).parameters) == 1:
        return target(obj)
    return target(obj, format_spec)


def compute_formatting_func(obj: T, format_spec: Spec) -> Target:
    """Uses the Formatters and formatmethods associated with obj to compute a formatting function.

    Raises SimpleFormatterError if obj has no associated Formatter(s)"""

    # get any formatmethod first and check if it takes take precedence
    format_method: Optional[formatmethod]
    try:
        format_method = lookup_formatmethod(obj, format_spec)
    except SimpleFormatterError:
        format_method = None
    else:
        # formatmethod with override comes first
        # TODO: return immediately if format_method overrides
        pass

    # the specifier target is next priority
    try:
        return compute_target(obj, format_spec)
    except SimpleFormatterError as e:
        if format_method is None:
            raise e
        else:
            # formatmethod with no override comes last
            return format_method


def compute_target(obj: T, format_spec: Spec) -> Target:
    """Retrieve the target given an object and format specifier.

    The Formatters associated with obj are combined to find the target.
    """

    # TODO: finish this -- broken right now
    # formattable decorator first
    try:
        return composite_cls_reg[type(obj)][format_spec]
    except KeyError:
        raise SimpleFormatterError(f"no class-level target for spec: {format_spec!r}")

    # target decorators second
    try:
        return composite_gen_reg.target_reg[format_spec]
    except KeyError:
        raise SimpleFormatterError(f"no target for spec: {format_spec!r}")

    # signal spec handling failure
    raise SimpleFormatterError(f"unhandled format_spec: {format_spec!r}")


def lookup_formatmethod(obj: T, format_spec: Spec) -> formatmethod:
    try:
        cls = type(obj)
        # perform lookup based on the cls's formatmethod-like objects (ie, objects with a SPECS attribute)
        # the MOST RECENTLY DEFINED method using the format_spec is the one we want
        return next(cls_member for cls_member in (getattr(cls, attr, None) for attr in reversed(dir(obj)))
                      if format_spec in getattr(cls_member, SPECS, ()))
    except StopIteration:
        raise SimpleFormatterError()


class formatmethod(Generic[T]):
    """formatmethod decorator. Accessed by specific format specifiers and returns a formatted version of the string."""

    def __init__(self, *specs: Union[Target, Spec], override: bool = False) -> None:

        method: Optional[Target] = None

        # first specifier may be decorator argument
        if specs:
            if callable(specs[0]):
                method, *specs = specs

        specs: Sequence[Spec]

        if method is not None:
            self(method.__func__ if hasattr(method, "__func__") else method)
        setattr(self, SPECS, specs if specs else ("",))

        # TODO: implement override

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
        """Use the target associated with format_spec to produce the formatted string version of value"""

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
