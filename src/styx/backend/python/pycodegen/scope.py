from __future__ import annotations


class Scope:
    """A scope for Python symbols."""

    def __init__(self, parent: Scope | None = None) -> None:
        """Create a scope."""
        self.parent: Scope | None = parent
        self._symbols: set[str] = set()

    def __contains__(self, symbol: str) -> bool:
        """Check if a symbol is in the scope."""
        if not isinstance(symbol, str):
            raise TypeError(f"Symbol must be a string, not {type(symbol)}")
        return symbol in self._symbols or (self.parent is not None and symbol in self.parent)

    def __repr__(self) -> str:
        """Get a string representation of the scope."""
        return f"Scope({self._symbols})"

    def _add_or_dodge(self, symbol: str, dodge: int) -> str:
        """Add a symbol to the scope, avoiding collisions."""
        if dodge == 0:
            dodge_name = symbol
        elif dodge == 1:
            dodge_name = f"{symbol}_"
        else:
            dodge_name = f"{symbol}_{dodge}"
        if dodge_name in self:
            return self._add_or_dodge(symbol, dodge + 1)
        else:
            return self.add_or_die(dodge_name)

    def add_or_dodge(self, symbol: str) -> str:
        """Add a symbol to the scope, avoiding collisions."""
        return self._add_or_dodge(symbol, 0)

    def add_or_die(self, symbol: str) -> str:
        """Add a symbol to the scope."""
        if not self._legal(symbol):
            raise ValueError(f"Symbol '{symbol}' is not a legal Python identifier")
        if symbol in self:
            raise ValueError(f"Symbol '{symbol}' already exists in scope")
        self._symbols.add(symbol)
        return symbol

    @classmethod
    def _legal(cls, symbol: str) -> bool:
        """Check if a symbol is legal."""
        return symbol.isidentifier()

    @classmethod
    def python(cls) -> Scope:
        """Create a scope with all Python keywords, standard library modules, and builtins."""
        import builtins
        import keyword
        import sys

        scope = Scope()

        for s in {
            *keyword.kwlist,
            *sys.stdlib_module_names,
            *dir(builtins),
            *dir(__builtins__),
        }:
            scope.add_or_die(s)

        return scope
