class Symbol:
    def __init__(self, name: str, symbol_type: str, kind: str = "variable", extra: dict = None):
        self.name = name
        self.symbol_type = symbol_type  # e.g., 'int', 'float', 'bool', 'string', 'int[]', 'void'
        self.kind = kind  # 'variable', 'function'
        self.extra = extra or {}  # e.g., parameter types for functions

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.symbol_type,
            "kind": self.kind,
            # 'params' in extra is a list of (name, type) tuples for functions;
            # convert to lists so it's valid JSON.
            "params": [list(p) for p in self.extra.get("params", [])] if self.extra.get("params") else None,
        }

class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def define(self, name: str, symbol: Symbol) -> bool:
        if name in self.symbols:
            return False  # Duplicate declaration in current scope
        self.symbols[name] = symbol
        return True

    def lookup(self, name: str) -> Symbol:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_current(self, name: str) -> Symbol:
        return self.symbols.get(name)

    def to_dict(self) -> dict:
        """Serialize this scope (not child/nested scopes, which aren't kept
        after type-checking finishes) into a JSON-friendly structure."""
        return {
            "scope": "global" if self.parent is None else "local",
            "symbols": [sym.to_dict() for sym in self.symbols.values()],
        }