class Symbol:
    def __init__(self, name: str, symbol_type: str, kind: str = "variable", extra: dict = None):
        self.name = name
        self.symbol_type = symbol_type  # e.g., 'int', 'float', 'bool', 'string', 'int[]', 'void'
        self.kind = kind  # 'variable', 'function'
        self.extra = extra or {}  # e.g., parameter types for functions

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