from __future__ import annotations

from inspect import signature
from itertools import repeat
from string import Formatter
from typing import Optional, NewType, Callable, Dict, Mapping, Generic, TypeVar, Type, Union, Sequence, Any, Iterable

SPECS = "specifiers"  # formatmethod specifiers holder attribute name
SPECS_TYPE_ERROR = "format specifiers must be {type_.__qualname__!s}, not {obj.__class__.__qualname__!s}"
DEFAULT_DUNDER_FORMAT = "_default__format__"  # attr name to keep reference to original __format__
FORMATTERS = "_formatters"  # attr name to keep reference to applied simpleformatter instances
OVERRIDE = "override"  # attr name to specify if a formatmethod should override a formatter target

T = TypeVar("T")
Spec = NewType("Spec", str)
ResultStr = NewType("ResultStr", str)
Target = Callable[..., ResultStr]
FormatRegister = Dict[Spec, Target]


class SimpleFormatterError(Exception):
    pass


def _new__format__(obj: Any, format_spec: Spec) -> ResultStr:
    """Replacement __format__ formatmethod for formattable decorated classes"""

    if not isinstance(format_spec, str):
        raise TypeError(f"__format__() argument must be str, not {type(format_spec).__qualname__!s}")

    target: Target
    try:
        target = compute_formatting_func(obj, format_spec)
    except SimpleFormatterError:
        try:
            target = getattr(type(obj), DEFAULT_DUNDER_FORMAT)
        except AttributeError:
            raise ValueError("invalid format specifier")

    # user defined targets *may* discard arguments for convenience
    # TODO: figure out if want to allow discarding self and keeping format_spec? how to do? check staticmethod??
    if len(signature(target).parameters) == 0:
        return target()
    if len(signature(target).parameters) == 1:
        return target(obj)
    return target(obj, format_spec)


def compute_formatting_func(obj: Any, format_spec: Spec) -> Target:
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

    cls = type(obj)
    empty_dict = dict()

    # build composite registries from formatters
    composite_cls_reg: FormatRegister = dict()
    composite_target_reg: FormatRegister = dict()

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


def lookup_formatmethod(obj: T, format_spec: Spec) -> formatmethod:
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


class formatmethod(Generic[T]):
    """formatmethod decorator. Accessed by _new__format__ returns a formatted version of the string."""

    def __init__(self, *specs: Union[Target, Spec], override: bool = False) -> None:

        method: Optional[Target] = None

        # first specifier may be decorator argument
        if specs and callable(specs[0]):
            method, *specs = specs

        check_types(specs, str, SPECS_TYPE_ERROR)

        specs: Sequence[Spec]

        if method is not None:
            self(method.__func__ if hasattr(method, "__func__") else method)
        setattr(self, SPECS, specs if specs else ("",))

        # TODO: implement override

    def __get__(self, instance, owner) -> Target:
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

    def target(self, *specs: Union[Target, Spec]) -> Target:

        method: Optional[Target] = None

        if specs and not isinstance(specs[0], str):
            method, *specs = specs

        check_types(specs, str, SPECS_TYPE_ERROR)

        def decorator(f: Target) -> Target:
            self.register_target(f, *specs)
            return f

        return decorator if method is None else decorator(method)

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


def check_types(objs: Any, types: Union[Type, Iterable[Type]], err_msgs: Union[str, Iterable[str]]) -> None:
    if isinstance(objs, str):
        objs=[objs]

    if not isinstance(types, Iterable):
        types = repeat(types)

    if isinstance(err_msgs, str) or not isinstance(err_msgs, Iterable):
        err_msgs = repeat(err_msgs)

    try:
        raise TypeError(next(msg.format(obj=obj, type_=type_) for obj, type_, msg in zip(objs, types, err_msgs)
                             if not isinstance(obj, type_)))
    except StopIteration:
        pass

