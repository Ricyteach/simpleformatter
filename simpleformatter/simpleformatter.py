from inspect import signature
from itertools import repeat
from typing import (Optional, NamedTuple, NewType, Callable, Dict, Mapping, TypeVar, Type, Union, Sequence, Any,
                    Iterable, Tuple)

Sentinel = type("Sentinel", (), {})
SENTINEL = Sentinel()
FORMATTERS = "_formatters"  # attr name to keep reference to applied simpleformatter instances
DEFAULT__FORMAT__ = "_default__format__"  # attr name to keep reference to original __format__
SPECS = "specifiers"  # formatmethod specifiers holder attribute name

# repeated error messages
SPECS_TYPE_ERROR = "format specifiers must be {type_name!s}, not {obj.__class__.__qualname__!s}"
TARGET_TYPE_ERROR = "format function targets must be {type_name!s}, not {obj.__class__.__qualname__!s}"

# for type hinting
T_Type = TypeVar("T_Type", bound=Type)
FormatString = NewType("FormatString", str)
FormatSpec = NewType("FormatSpec", str)
Target = Callable[..., FormatString]
TargetDecorator = Callable[[Target], Target]
Registry = Mapping[FormatSpec, Target]
FormatDict = Dict[FormatSpec, Target]


class SimpleFormatterError(Exception):
    pass


class Resolution(NamedTuple):
    """The outcome of resolving a format spec.

    `spec` is the registered specifier that was matched, and `std_spec` is whatever preceded it in the format spec.
    For an exact match `spec` is the whole format spec and `std_spec` is empty; for a suffix match on, say, '.3ft',
    `spec` is 'ft' and `std_spec` is '.3'.
    """

    target: Target
    spec: FormatSpec
    std_spec: FormatSpec = ""


class MethodMatch(NamedTuple):
    """A formatmethod matched against a format spec, with the specifier it matched and whatever preceded it.

    Split out from Resolution because the priority rules need the formatmethod itself, to consult its override flag.
    """

    method: 'formatmethod'
    spec: FormatSpec
    std_spec: FormatSpec = ""


def _new__format__(self: Any, format_spec: FormatSpec) -> FormatString:
    """Replacement __format__ formatmethod for formattable decorated classes"""

    if not isinstance(format_spec, str):
        raise TypeError(f"__format__() argument must be str, not {type(format_spec).__qualname__!s}")

    resolution: Resolution
    try:
        resolution = compute_formatting_func(self, format_spec)
    except SimpleFormatterError:
        default__format__: Target
        try:
            default__format__ = getattr(type(self), DEFAULT__FORMAT__)
        except AttributeError:
            raise ValueError("invalid format specifier")
        else:
            return default__format__(self, format_spec)

    # user defined targets *may* discard arguments for convenience
    # TODO: figure out if want to allow discarding self and keeping format_spec? how to do? check staticmethod??
    param_count = len(signature(resolution.target).parameters)
    if param_count == 0:
        return resolution.target()
    if param_count == 1:
        return resolution.target(self)
    if param_count == 2:
        return resolution.target(self, resolution.spec)
    return resolution.target(self, resolution.spec, resolution.std_spec)


def compute_formatting_func(obj: Any, format_spec: FormatSpec) -> Resolution:
    """Uses the SimpleFormatters and formatmethods associated with obj to compute a formatting function.

    Raises SimpleFormatterError if obj has no associated SimpleFormatter for that format specifier.
    """

    # get any formatmethod first and check if it is set to override
    match: Optional[MethodMatch]
    try:
        match = lookup_formatmethod(obj, format_spec)
    except SimpleFormatterError:
        match = None
    else:
        # formatmethod with override comes first
        if match.method.override:
            return Resolution(match.method.__func__, match.spec, match.std_spec)

    # the specifier target is next priority
    try:
        return compute_target(obj, format_spec)
    except SimpleFormatterError as e:
        if match is None:
            raise e
        else:
            # formatmethod with no override comes last
            return Resolution(match.method.__func__, match.spec, match.std_spec)


def compute_target(obj: Any, format_spec: FormatSpec) -> Resolution:
    """Retrieve the target formatting function given an object and format specifier.

    The SimpleFormatters associated with obj are combined to find the target. Exact specifier matches are preferred;
    failing that, the longest suffix-registered specifier the format spec ends with wins.
    """

    cls = type(obj)
    empty_dict = dict()

    # build composite registries from formatters
    composite_cls_reg: FormatDict = dict()
    composite_target_reg: FormatDict = dict()
    composite_suffix_reg: FormatDict = dict()

    fmtr: SimpleFormatter
    for fmtr in getattr(obj, FORMATTERS):
        composite_cls_reg.update(fmtr.cls_reg.get(cls, empty_dict))
        composite_target_reg.update(fmtr.target_reg)
        composite_suffix_reg.update(fmtr.suffix_reg)

    # exact matches first: formattable decorator, then target decorators
    for reg in (composite_cls_reg, composite_target_reg):
        try:
            return Resolution(reg[format_spec], format_spec)
        except KeyError:
            pass

    # then the longest suffix-registered specifier, so that eg '.3ft' resolves to the 'ft' target with '.3' left over
    # (longest first means 'mm' beats 'm', and a suffix match is unique for any given length)
    for spec in sorted(composite_suffix_reg, key=len, reverse=True):
        if format_spec.endswith(spec):
            return Resolution(composite_suffix_reg[spec], spec, format_spec[:-len(spec)])

    # signal spec handling failure
    raise SimpleFormatterError(f"unhandled format_spec: {format_spec!r}")


def lookup_formatmethod(obj: Any, format_spec: FormatSpec) -> MethodMatch:
    """Retrieve the obj formatmethod that utilizes the format_spec, if it exists.

    An exact specifier match wins. Failing that, the longest suffix among the formatmethods declared with
    suffix=True is used, so '.2MB' can resolve to a formatmethod registered for 'MB'.

    Raises SimpleFormatterError if one is not found.
    """

    cls = type(obj)
    # perform lookup based on the cls's formatmethod-like objects (ie, objects with a SPECS attribute)
    # the MOST RECENTLY DEFINED method using the format_spec is the one we want
    cls_members = [getattr(cls, attr, None) for attr in reversed(dir(obj))]

    for cls_member in cls_members:
        if format_spec in getattr(cls_member, SPECS, ()):
            return MethodMatch(cls_member, format_spec)

    # no exact match, so fall back to the longest suffix declared by a suffix formatmethod; the empty specifier is
    # skipped because it is a suffix of every format spec there is
    best: Optional[Tuple[Any, FormatSpec]] = None
    for cls_member in cls_members:
        if not getattr(cls_member, "suffix", False):
            continue
        for spec in getattr(cls_member, SPECS, ()):
            if spec and format_spec.endswith(spec) and (best is None or len(spec) > len(best[1])):
                best = (cls_member, spec)

    if best is None:
        raise SimpleFormatterError()

    cls_member, spec = best
    return MethodMatch(cls_member, spec, format_spec[:-len(spec)])


class formatmethod:
    """formatmethod decorator, applied to formattable class methods that return a string representation of an instance.

    Optionally provide specifier strings (no spec provided means the method will be used when there is no spec).

    >>> @formattable
    ... class C:
    ...     @formatmethod
    ...     def my_formatter1(self):
    ...         return "Formatted C object"
    ...     @formatmethod("spec")
    ...     def my_formatter2(self):
    ...         return "Formatted C object spec"
    ...
    >>> f"{C()}"  # no specifier, my_formatter1 called
    'Formatted C object'
    >>> f"{C():spec}"  # 'spec' specifier, my_formatter2 called
    'Formatted C object spec'

    Pass suffix=True to match the specifier at the *end* of a format spec rather than as the whole of it. The method
    may then take a third argument, which receives the standard format spec preceding the specifier:

    >>> @formattable
    ... class Data(float):
    ...     @formatmethod('MB', suffix=True)
    ...     def _repr_mb_(self, spec, std_spec):
    ...         return f'{self / 1024 ** 2:{std_spec}} {spec}'
    ...
    >>> f'{Data(112_113_254):.2fMB}'
    '106.92 MB'

    The empty specifier is never treated as a suffix, since it would match every format spec there is.
    """

    def __init__(self, *specs: Union[Target, FormatSpec], override: bool = False, suffix: bool = False) -> None:

        self.override: bool = override
        self.suffix: bool = suffix

        method: Union[Sentinel, Target] = SENTINEL

        # first specifier may be decorator argument
        if specs and not isinstance(specs[0], str):
            method: Target
            specs: Sequence[FormatSpec]
            method, *specs = specs

        check_types(specs, str, SPECS_TYPE_ERROR)

        # associate specs with this formatmethod, and guard against double decorators, no specs == empty string spec
        setattr(self, SPECS, set(specs) if specs else {""})

        # apply decorator if called with no arguments
        if method is not SENTINEL:
            self(method)

    def __get__(self, instance, owner) -> Target:
        if instance is not None:
            return self.__func__.__get__(instance, owner)
        return self

    def __call__(self, method: Target) -> 'formatmethod':
        check_types(method, Callable, TARGET_TYPE_ERROR)
        getattr(self, SPECS).update(getattr(method, SPECS, set()))
        # stacked formatmethods union their specifiers, so union the suffix flag along with them
        self.suffix = self.suffix or getattr(method, "suffix", False)
        self._method = getattr(method, "__func__", method)
        return self

    @property
    def __func__(self) -> Target:
        """The formatting method decorated by formatmethod"""

        return self._method

    def __str__(self):
        return f"{type(self).__qualname__}({self.__func__.__name__})"


class SimpleFormatter:
    """Handles dispatch to formatting functions based on specifier strings.

    The following API decorators are methods of this class:
    - formattable
    - target

    An instance of this class, as well as references to the API decorators, are provided at the top level of the package
    for convenience:
    >>> from simpleformatter import simpleformatter  # convenience instance
    >>> from simpleformatter import formattable  # decorator for classes
    >>> from simpleformatter import target  # decorator for formatting functions
    """

    target_reg: FormatDict
    suffix_reg: FormatDict
    cls_reg: Dict[Type, FormatDict]

    def __init__(self) -> None:
        self.target_reg = dict()
        self.suffix_reg = dict()
        self.cls_reg = dict()

    def formattable(self, cls: Optional[T_Type] = None, **kwargs: Target) -> Union[T_Type, Callable[[T_Type], T_Type]]:
        """formattable decorator, applied to classes. Decorated class is registered with the SimpleFormatter, and
        cls.__format__ is overridden.

        Optionally provide kwarg(s) that map specifier strings to formatting functions. Because they are passed as
        kwargs, specifiers registered this way have to be valid identifiers; use `target` or `formatmethod` to handle
        the empty specifier.

        >>> def my_formatter1(obj):
        ...     return 'my_formatter1 formatted the object'
        ...
        >>> def my_formatter2(obj, spec):  # a second argument for the spec is optional
        ...     return f'my_formatter2 formatted the object with {spec}'
        ...
        >>> @formattable(spec1=my_formatter1, spec2=my_formatter2)
        ... class C: ...
        ...
        >>> f"{C():spec1}"  # 'spec1' specifier, my_formatter1 called
        'my_formatter1 formatted the object'
        >>> f"{C():spec2}"  # 'spec2' specifier, my_formatter2 called
        'my_formatter2 formatted the object with spec2'
        """

        def formattable_dec(dec_cls: T_Type) -> T_Type:
            self.register_cls(dec_cls, kwargs)
            return dec_cls

        return formattable_dec if cls is None else formattable_dec(cls)

    def target(self, *specs: Union[Target, FormatSpec],
               suffix: bool = False) -> Union[Target, TargetDecorator]:
        """target decorator, applied to functions that return a string representation of some formattable object.

        Optionally provide specifier strings (no spec provided means the function will be used when there is no spec).

        >>> @target
        ... def my_formatter1(obj):
        ...     return 'my_formatter1 formatted the object'
        ...
        >>> @target('spec')
        ... def my_formatter2(obj, spec):  # a second argument for the spec is optional
        ...     return f'my_formatter2 formatted the object with {spec}'
        ...
        >>> @formattable
        ... class C: ...
        ...
        >>> f"{C()}"  # no specifier, my_formatter1 called
        'my_formatter1 formatted the object'
        >>> f"{C():spec}"  # 'spec' specifier, my_formatter2 called
        'my_formatter2 formatted the object with spec'

        Pass suffix=True to match the specifier at the *end* of a format spec rather than as the whole of it. The
        function may then take a third argument, which receives the standard format spec preceding the specifier:

        >>> @target('ft', suffix=True)
        ... def to_feet(inches, spec, std_spec):
        ...     return f'{inches / 12:{std_spec}} {spec}'
        ...
        >>> @formattable
        ... class Inches(float): ...
        ...
        >>> f"{Inches(8.45):.3ft}"
        '0.704 ft'

        When several suffix specifiers match, the longest wins, so 'mm' is preferred over 'm'. Take care registering
        suffix specifiers that collide with the built-in presentation types (b, c, d, e, E, f, F, g, G, n, o, s, x,
        X and %): registering 'f' as a suffix would capture '.2f' and shadow ordinary float formatting.
        """

        func: Union[Sentinel, Target] = SENTINEL

        if specs and not isinstance(specs[0], str):
            specs: Sequence[FormatSpec]
            func, *specs = specs

        def target_dec(func: Target) -> Target:
            self.register_target(func, specs, suffix)
            return func

        return target_dec if func is SENTINEL else target_dec(func)

    def register_cls(self, cls: Type, reg: Registry) -> None:
        """Associate the cls with the SimpleFormatter instance for formatting."""

        # if not previously done for this class, override the __format__ method, keep a reference to the old one
        setattr(cls, DEFAULT__FORMAT__, getattr(cls, DEFAULT__FORMAT__, cls.__format__))
        cls.__format__ = _new__format__

        # add the SimpleFormatter to the SF list (create the list if this is the first one)
        try:
            formatters = getattr(cls, FORMATTERS)
        except AttributeError:
            setattr(cls, FORMATTERS, [self])
        else:
            formatters.append(self)

        # update the cls registry with reg, or use reg as the new registry if cls registry doesn't exist
        try:
            self.cls_reg[cls].update(reg)
        except KeyError:
            self.cls_reg[cls] = reg

    def register_target(self, target: Target, specs: Union[FormatSpec, Iterable[FormatSpec]],
                        suffix: bool = False) -> None:
        """Associate the target formatting function with the SimpleFormatter instance for formatting.

        With suffix=True the specifiers match the end of a format spec instead of the whole of it.
        """

        specs_tup: Tuple[FormatSpec] = (specs,) if isinstance(specs, str) else tuple(specs)
        check_types(specs_tup, str, SPECS_TYPE_ERROR)
        check_types(target, Callable, TARGET_TYPE_ERROR)

        # no specs == empty string spec, matching formatmethod
        if not specs_tup:
            specs_tup = ("",)

        # update the appropriate registry with the specifiers; the empty specifier is never a suffix, since it would
        # match every format spec there is
        for spec in specs_tup:
            reg = self.suffix_reg if (suffix and spec) else self.target_reg
            reg[spec] = target


def check_types(objs: Any, types: Union[Type, Iterable[Type]], err_msgs: Union[str, Iterable[str]]) -> None:
    """Utility for enforcing type requirements on arguments.

    Error message strings use the kwargs ``type_``, ``type_name`` and ``obj``, and can be of these forms, or
    variants::

        "arg1 must be {type_.__qualname__!s}, not {obj.__class__.__qualname__!s}"
        "arg1 must be {type_name!s}, not {obj.__class__.__qualname__!s}"
    """

    if isinstance(objs, str) or not isinstance(objs, Iterable):
        objs = objs,

    if not isinstance(types, Iterable):
        types = repeat(types)

    if isinstance(err_msgs, str) or not isinstance(err_msgs, Iterable):
        err_msgs = repeat(err_msgs)

    for obj, type_, msg in zip(objs, types, err_msgs):
        try:
            assert isinstance(obj, type_)
        except AssertionError:
            raise TypeError(msg.format(obj=obj, type_=type_, type_name=getattr(type_, '__qualname__', str(type_))))
