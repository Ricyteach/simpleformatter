from __future__ import annotations

from inspect import signature
from itertools import repeat
from string import Formatter
from typing import Optional, NewType, Callable, Dict, Mapping, Generic, TypeVar, Type, Union, Sequence, Any, Iterable, \
    Tuple

Sentinel = type("Sentinel", (), {})
SENTINEL = Sentinel()
FORMATTERS = "_formatters"  # attr name to keep reference to applied simpleformatter instances
DEFAULT__FORMAT__ = "_default__format__"  # attr name to keep reference to original __format__
SPECS = "specifiers"  # formatmethod specifiers holder attribute name
SPECS_TYPE_ERROR = "format specifiers must be {type_name!s}, not {obj.__class__.__qualname__!s}"
TARGET_TYPE_ERROR = "format function targets must be {type_name!s}, not {obj.__class__.__qualname__!s}"

T = TypeVar("T")
FormatString = NewType("FormatString", str)
FormatSpec = NewType("FormatSpec", str)
Target = Callable[..., FormatString]
Registry = Mapping[FormatSpec, Target]
FormatDict = Dict[FormatSpec, Target]


class SimpleFormatterError(Exception):
    pass


def _new__format__(self: Any, format_spec: FormatSpec) -> FormatString:
    """Replacement __format__ formatmethod for formattable decorated classes"""

    if not isinstance(format_spec, str):
        raise TypeError(f"__format__() argument must be str, not {type(format_spec).__qualname__!s}")

    target: Target
    try:
        target = compute_formatting_func(self, format_spec)
    except SimpleFormatterError:
        try:
            target = getattr(type(self), DEFAULT__FORMAT__)
        except AttributeError:
            raise ValueError("invalid format specifier")
        else:
            return target(self, format_spec)

    # user defined targets *may* discard arguments for convenience
    # TODO: figure out if want to allow discarding self and keeping format_spec? how to do? check staticmethod??
    if len(signature(target).parameters) == 0:
        return target()
    if len(signature(target).parameters) == 1:
        return target(self)
    return target(self, format_spec)


def compute_formatting_func(obj: Any, format_spec: FormatSpec) -> Target:
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
        if format_method.override:
            return format_method.__func__

    # the specifier target is next priority
    try:
        return compute_target(obj, format_spec)
    except SimpleFormatterError as e:
        if format_method is None:
            raise e
        else:
            # formatmethod with no override comes last
            return format_method.__func__


def compute_target(obj: Any, format_spec: FormatSpec) -> Target:
    """Retrieve the target given an object and format specifier.

    The formatters associated with obj are combined to find the target.
    """

    cls = type(obj)
    empty_dict = dict()

    # build composite registries from formatters
    composite_cls_reg: FormatDict = dict()
    composite_target_reg: FormatDict = dict()

    fmtr: SimpleFormatter
    for fmtr in getattr(obj, FORMATTERS):
        composite_cls_reg.update(fmtr.cls_reg.get(cls, empty_dict))
        composite_target_reg.update(fmtr.target_reg)

    try:
        # formattable decorator first
        return composite_cls_reg[format_spec]
    except KeyError:
        try:
            # target decorators second
            return composite_target_reg[format_spec]
        except KeyError:
            # signal spec handling failure
            raise SimpleFormatterError(f"unhandled format_spec: {format_spec!r}")


def lookup_formatmethod(obj: Any, format_spec: FormatSpec) -> formatmethod:
    """Retrieve the obj formatmethod that utilizes the format_spec, if it exists.

    Raises SimpleFormatterError if one is not found."""

    try:
        cls = type(obj)
        # perform lookup based on the cls's formatmethod-like objects (ie, objects with a SPECS attribute)
        # the MOST RECENTLY DEFINED method using the format_spec is the one we want
        return next(cls_member for cls_member in (getattr(cls, attr, None) for attr in reversed(dir(obj)))
                      if format_spec in getattr(cls_member, SPECS, ()))
    except StopIteration:
        raise SimpleFormatterError()


class formatmethod:
    """formatmethod decorator. Accessed by _new__format__ returns a formatted version of the string."""

    def __init__(self, *specs: Union[Target, FormatSpec], override: bool = False) -> None:

        self.override: bool = override

        method: Union[Sentinel, Target] = SENTINEL

        # first specifier may be decorator argument
        if specs and not isinstance(specs[0], str):
            method: Target
            specs: Sequence[FormatSpec]
            method, *specs = specs

        check_types(specs, str, SPECS_TYPE_ERROR)

        # associate specs with this formatmethod, and guard against double decorators, no specs == empty string spec
        setattr(self, SPECS, set(specs) if specs else {"",})

        # apply decorator if called with no arguments
        if method is not SENTINEL:
            self(method)

    def __get__(self, instance, owner) -> Target:
        if instance is not None:
            return self.__func__.__get__(instance, owner)
        return self

    def __call__(self, method: Target) -> formatmethod:
        check_types(method, Callable, TARGET_TYPE_ERROR)
        getattr(self, SPECS).update(getattr(method, SPECS, set()))
        self._method = getattr(method, "__func__", method)
        return self

    @property
    def __func__(self) -> Target:
        return self._method

    def __str__(self):
        return f"{type(self).__qualname__}({self.__func__.__name__})"


class SimpleFormatter(Formatter, Generic[T]):

    target_reg: FormatDict
    cls_reg: Dict[Type[T], FormatDict]

    def __init__(self) -> None:
        self.target_reg = dict()
        self.cls_reg = dict()

    def formattable(self, cls: Optional[Type[T]] = None, *, reg: Optional[Registry] = None,
                    **target_kwargs: Target) -> Union[Type[T], Callable[[Type[T]],Type[T]]]:

        if reg is None:
            reg = dict()

        def formattable_dec(dec_cls: Type[T]) -> Type[T]:
            reg.update(**target_kwargs)
            self.register_cls(dec_cls, reg)
            return dec_cls

        return formattable_dec if cls is None else formattable_dec(cls)

    def target(self, *specs: Union[Target, FormatSpec]) -> Target:

        func: Union[Sentinel, Target] = SENTINEL

        if specs and not isinstance(specs[0], str):
            specs: Sequence[FormatSpec]
            func, *specs = specs

        def target_dec(func: Target) -> Target:
            self.register_target(func, specs)
            return func

        return target_dec if func is SENTINEL else target_dec(func)

    def format_field(self, value: T, format_spec: FormatSpec) -> FormatString:
        """Use the target associated with format_spec to produce the formatted string version of value"""

    def lookup_cls_target(self: SimpleFormatter, obj: T, format_spec: FormatSpec) -> Target:
        try:
            return self.cls_reg[type(obj)][format_spec]
        except KeyError:
            raise SimpleFormatterError(f"no class-level target for spec: {format_spec!r}")

    def lookup_gen_target(self: SimpleFormatter, format_spec: FormatSpec) -> Target:
        try:
            return self.target_reg[format_spec]
        except KeyError:
            raise SimpleFormatterError(f"no target for spec: {format_spec!r}")

    def register_cls(self, cls: Type[T], reg: Registry) -> None:
        setattr(cls, DEFAULT__FORMAT__, getattr(cls, DEFAULT__FORMAT__, cls.__format__))
        cls.__format__ = _new__format__

        try:
            formatters = getattr(cls, FORMATTERS)
        except AttributeError:
            setattr(cls, FORMATTERS, [self])
        else:
            formatters.append(self)

        try:
            self.cls_reg[cls].update(reg)
        except KeyError:
            self.cls_reg[cls] = reg

    def register_target(self, target: Target, specs: Union[FormatSpec, Iterable[FormatSpec]]) -> None:
        specs_tup: Tuple[FormatSpec] = (specs,) if isinstance(specs, str) else tuple(specs)
        check_types(specs_tup, str, SPECS_TYPE_ERROR)
        check_types(target, Callable, TARGET_TYPE_ERROR)

        self.target_reg.update(zip(specs_tup, repeat(target)))


def check_types(objs: Any, types: Union[Type, Iterable[Type]], err_msgs: Union[str, Iterable[str]]) -> None:
    if isinstance(objs, str) or not isinstance(objs, Iterable):
        objs = objs,

    if not isinstance(types, Iterable):
        types = repeat(types)

    if isinstance(err_msgs, str) or not isinstance(err_msgs, Iterable):
        err_msgs = repeat(err_msgs)

    try:
        raise TypeError(next(msg.format(obj=obj, type_name=getattr(type_,"__qualname__",str(type_)))
                             for obj, type_, msg in zip(objs, types, err_msgs)
                             if not isinstance(obj, type_)))
    except StopIteration:
        pass
