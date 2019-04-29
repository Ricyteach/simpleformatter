from __future__ import annotations
from string import Formatter
from typing import Optional, NewType, Callable, Dict, Mapping, Generic, TypeVar, Type

SPECS = "specs"  # formatmethod specs holder attribute name

F_co = TypeVar("F_co", covariant=True)
T_co = TypeVar("T_co", covariant=True)
Spec = NewType("Spec", str)
ResultStr = NewType("ResultStr", str)
Target = Callable[[T_co, Spec], ResultStr]
FormatRegister = Dict[Spec, Target]


class SimpleFormatterError(Exception):
    pass


class formatmethod(Generic[T_co]):
    """Create a method that is accessed by specific format specs and returns a formatted version of the string."""

    def __init__(self, method: Optional[Target] = None, *specs: Spec):
        setattr(self, SPECS, specs if specs else ("",))

        if method is not None:
            self(method)

    def __get__(self, instance, owner):
        if instance is not None:
            return self.__func__.__get__(instance, owner)
        return self

    def __call__(self, method: Target):
        self._method = method
        return self

    @property
    def __func__(self):
        return self._method


def lookup_formatmethod(obj: T_co, format_spec: Spec) -> Target:
    try:
        *_, m_name = (attr for attr, member in ((attr, getattr(obj, attr)) for attr in dir(obj))
                      if format_spec in getattr(member, SPECS, ()))
    except ValueError:
        raise SimpleFormatterError()
    return getattr(obj, m_name)


class RegistryManager(Generic[F_co, T_co]):

    def __init__(self, registration_client: F_co):
        self._holder = registration_client

    def cls(self, obj: T_co, format_spec: Spec) -> Target:
        try:
            return self.cls_reg[type(obj)][format_spec]
        except KeyError:
            raise SimpleFormatterError(f"no class-level target for spec: {format_spec!r}")

    def target(self, format_spec: Spec) -> Target:
        try:
            return self.gen_reg[format_spec]
        except KeyError:
            raise SimpleFormatterError(f"no target for spec: {format_spec!r}")

    @property
    def cls_reg(self):
        return self._holder.cls_reg

    @property
    def gen_reg(self):
        return self._holder.gen_reg

class SimpleFormatter(Formatter, Generic[T_co]):

    gen_reg: FormatRegister
    cls_reg: Dict[Type[T_co], FormatRegister]
    _reg_manager: RegistryManager[SimpleFormatter[T_co], T_co]

    def __init__(self):
        self.gen_reg = dict()
        self.cls_reg = dict()
        self._reg_manager = RegistryManager[type(self)[T_co], T_co](self)

    def formattable(self, cls: Optional[Type[T_co]] = None, *, formatter_dict: Optional[Mapping[Spec, Target]]=None,
                    **formatter_kwargs: Target) -> Type[T_co]:

        def decorator(c: Type[T_co]) -> Type[T_co]:
            return c

        return decorator if cls is None else decorator(cls)

    def target(self, func: Optional[Target] = None, *specs: Spec) -> Target:

        def decorator(f: Target) -> Target:
            return f

        return decorator if func is None else decorator(func)

    def format_field(self, value: T_co, format_spec: Spec) -> ResultStr:
        try:
            handler = self.handle_spec(value, format_spec)
        except SimpleFormatterError:
            handler = super().format_field
        return handler(value, format_spec)

    def handle_spec(self, obj: T_co, format_spec: Spec) -> Target:
        # formattable decorator first
        try:
            return self._reg_manager.cls(obj, format_spec)
        except SimpleFormatterError:
            pass
        # formatmethod decorators second
        try:
            return lookup_formatmethod(obj, format_spec)
        except SimpleFormatterError:
            pass
        # target decorators third
        try:
            return self._reg_manager.target(format_spec)
        except SimpleFormatterError:
            pass
        # signal spec handling failure
        raise SimpleFormatterError(f"unhandled format_spec: {format_spec!r}")
