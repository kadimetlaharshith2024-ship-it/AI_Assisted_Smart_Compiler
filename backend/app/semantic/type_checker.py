from app.semantic.visitor import NodeVisitor
from app.semantic.symbol_table import SymbolTable, Symbol

UNKNOWN = "unknown"      # produced after an error so one mistake doesn't cascade
EMPTY_ARRAY = "[]"       # type of the literal `[]`; assignable to any array type
NUMERIC = ("int", "float")
ARITHMETIC_OPS = ("+", "-", "*", "/", "%")
ORDERING_OPS = ("<", ">", "<=", ">=")
EQUALITY_OPS = ("==", "!=")
LOGICAL_OPS = ("&&", "||")


def is_array(t):
    return t.endswith("[]")


def element_type(t):
    return UNKNOWN if t == EMPTY_ARRAY else t[:-2]


def compatible(expected, actual):
    """Can a value of type `actual` be used where `expected` is required?"""
    if UNKNOWN in (expected, actual) or expected == actual:
        return True
    if expected == "float" and actual == "int":      # int widens to float
        return True
    return is_array(expected) and actual == EMPTY_ARRAY


class SemanticError(Exception):
    def __init__(self, message, line=0):
        self.message = message
        self.line = line
        super().__init__(self.message)


class TypeChecker(NodeVisitor):
    def __init__(self):
        self.global_scope = SymbolTable()
        self.current_scope = self.global_scope
        self.errors = []
        self.current_function = None
        self.loop_depth = 0

        self.global_scope.define("print", Symbol("print", "function", kind="function"))

    # ---- helpers ----

    def error(self, message, line=0):
        self.errors.append({"line": line, "message": message})

    def visit(self, node, *args, **kwargs):
        if node is None:
            return None
        visitor = getattr(self, f"visit_{type(node).__name__}", self.generic_visit)
        return visitor(node, *args, **kwargs)

    def _expr(self, node, expected=None):
        """Visit an expression; `expected` lets array literals check themselves
        against the declared element type (so `let f: float[] = [1, 2]` works)."""
        if type(node).__name__ == "ArrayLiteralNode":
            return self.visit_ArrayLiteralNode(node, expected)
        return self.visit(node)

    @staticmethod
    def _hint(expected):
        return expected if expected and is_array(expected) else None

    def _push_scope(self):
        self.current_scope = SymbolTable(parent=self.current_scope)

    def _pop_scope(self):
        self.current_scope = self.current_scope.parent

    def _visit_block(self, block):
        """Visit a { ... } block in its own scope (matches the interpreter)."""
        if block is None:
            return
        self._push_scope()
        for stmt in getattr(block, "statements", []):
            self.visit(stmt)
        self._pop_scope()

    def _check_condition(self, node, what):
        t = self.visit(node)
        if t not in ("bool", UNKNOWN):
            self.error(f"{what} condition must be of type 'bool', got '{t}'", getattr(node, "line", 0))

    # ---- program / declarations ----

    def visit_ProgramNode(self, node):
        statements = getattr(node, "statements", [])

        # Pass 1: register top-level functions (forward references, recursion)
        for stmt in statements:
            if type(stmt).__name__ == "FunctionDeclNode":
                symbol = Symbol(stmt.name, stmt.return_type, kind="function", extra={"params": stmt.params})
                if not self.current_scope.define(stmt.name, symbol):
                    self.error(f"Function '{stmt.name}' is already declared", stmt.line)

        # Pass 2: check everything
        for stmt in statements:
            self.visit(stmt)

        return sorted(self.errors, key=lambda e: e["line"])

    def visit_BlockNode(self, node):
        self._visit_block(node)

    def visit_FunctionDeclNode(self, node):
        if self.current_scope is not self.global_scope or self.current_function is not None:
            self.error(f"Function '{node.name}' must be declared at the top level", node.line)
            return

        prev_scope, prev_loops = self.current_scope, self.loop_depth
        self.current_scope = SymbolTable(parent=prev_scope)
        self.current_function = node
        self.loop_depth = 0

        seen = set()
        for param_name, param_type in node.params:
            if param_name in seen:
                self.error(f"Duplicate parameter '{param_name}' in function '{node.name}'", node.line)
            seen.add(param_name)
            if param_type == "void":
                self.error(f"Parameter '{param_name}' cannot have type 'void'", node.line)
            self.current_scope.define(param_name, Symbol(param_name, param_type, kind="variable"))

        for stmt in getattr(node.body, "statements", []):
            self.visit(stmt)

        if node.return_type != "void" and not self._returns(node.body.statements):
            self.error(f"Function '{node.name}' must return a value of type '{node.return_type}' on every path", node.line)

        self.current_scope, self.current_function, self.loop_depth = prev_scope, None, prev_loops

    # ---- "does every path return?" ----

    def _returns(self, statements):
        return any(self._stmt_returns(s) for s in statements)

    def _stmt_returns(self, stmt):
        name = type(stmt).__name__
        if name == "ReturnNode":
            return True
        if name == "BlockNode":
            return self._returns(stmt.statements)
        if name == "IfNode" and stmt.else_branch is not None:
            branches = [stmt.then_branch] + [b for _, b in (stmt.elif_branches or [])] + [stmt.else_branch]
            return all(self._returns(b.statements) for b in branches)
        return False

    # ---- statements ----

    def visit_VarDeclNode(self, node):
        line = getattr(node, "line", 0)
        if node.var_type == "void":
            self.error(f"Variable '{node.name}' cannot have type 'void'", line)
        if node.value is not None:
            actual = self._expr(node.value, self._hint(node.var_type))
            if not compatible(node.var_type, actual):
                self.error(f"Cannot initialize '{node.name}' of type '{node.var_type}' with a value of type '{actual}'", line)
        if not self.current_scope.define(node.name, Symbol(node.name, node.var_type, kind="variable")):
            self.error(f"Variable '{node.name}' is already declared in this scope", line)

    def visit_AssignNode(self, node):
        line = getattr(node, "line", 0)
        target = node.target
        if type(target).__name__ == "IdentifierNode":
            symbol = self.current_scope.lookup(target.name)
            if symbol is None:
                self.error(f"Undeclared identifier '{target.name}'", target.line)
                target_type = UNKNOWN
            elif symbol.kind == "function":
                self.error(f"Cannot assign to function '{target.name}'", line)
                target_type = UNKNOWN
            else:
                target_type = symbol.symbol_type
            what = f"variable '{target.name}'"
        else:
            target_type = self.visit(target)
            what = "an array element"

        actual = self._expr(node.value, self._hint(target_type))
        if not compatible(target_type, actual):
            self.error(f"Cannot assign a value of type '{actual}' to {what} of type '{target_type}'", line)

    def visit_PrintNode(self, node):
        if node.expression is not None and self.visit(node.expression) == "void":
            self.error("Cannot print a 'void' value", getattr(node, "line", 0))

    def visit_IfNode(self, node):
        self._check_condition(node.condition, "'if'")
        self._visit_block(node.then_branch)
        for cond, block in node.elif_branches or []:
            self._check_condition(cond, "'else if'")
            self._visit_block(block)
        self._visit_block(node.else_branch)

    def visit_WhileNode(self, node):
        self._check_condition(node.condition, "'while'")
        self.loop_depth += 1
        self._visit_block(node.body)
        self.loop_depth -= 1

    def visit_ForNode(self, node):
        self._push_scope()
        if node.init is not None:
            self.visit(node.init)
        if node.condition is not None:
            self._check_condition(node.condition, "'for'")
        if node.update is not None:
            self.visit(node.update)
        self.loop_depth += 1
        self._visit_block(node.body)
        self.loop_depth -= 1
        self._pop_scope()

    def visit_ForEachNode(self, node):
        iterable_type = self.visit(node.iterable)
        if iterable_type == UNKNOWN:
            item_type = UNKNOWN
        elif not is_array(iterable_type):
            self.error(f"'foreach' requires an array, got '{iterable_type}'", node.line)
            item_type = UNKNOWN
        else:
            item_type = element_type(iterable_type)

        self._push_scope()
        self.current_scope.define(node.item_name, Symbol(node.item_name, item_type, kind="variable"))
        self.loop_depth += 1
        self._visit_block(node.body)
        self.loop_depth -= 1
        self._pop_scope()

    def visit_BreakNode(self, node):
        if self.loop_depth == 0:
            self.error("'break' can only be used inside a loop", node.line)

    def visit_ContinueNode(self, node):
        if self.loop_depth == 0:
            self.error("'continue' can only be used inside a loop", node.line)

    def visit_ReturnNode(self, node):
        fn = self.current_function
        if fn is None:
            self.error("'return' can only be used inside a function", node.line)
            if node.expression is not None:
                self.visit(node.expression)
            return

        expected = fn.return_type
        if node.expression is None:
            if expected != "void":
                self.error(f"Function '{fn.name}' must return a value of type '{expected}'", node.line)
            return

        actual = self._expr(node.expression, self._hint(expected))
        if expected == "void":
            self.error(f"Function '{fn.name}' is declared 'void' and cannot return a value", node.line)
        elif not compatible(expected, actual):
            self.error(f"Function '{fn.name}' must return '{expected}', but this returns '{actual}'", node.line)

    # ---- expressions ----

    def visit_IntLiteralNode(self, node):
        return "int"

    def visit_FloatLiteralNode(self, node):
        return "float"

    def visit_StringLiteralNode(self, node):
        return "string"

    def visit_BoolLiteralNode(self, node):
        return "bool"

    def visit_IdentifierNode(self, node):
        symbol = self.current_scope.lookup(node.name)
        if not symbol:
            self.error(f"Undeclared identifier '{node.name}'", node.line)
            return UNKNOWN
        if symbol.kind == "function":
            self.error(f"'{node.name}' is a function and cannot be used as a value", node.line)
            return UNKNOWN
        return symbol.symbol_type

    def visit_ArrayLiteralNode(self, node, expected=None):
        types = [self.visit(el) for el in node.elements]
        line = node.line

        if any(t != UNKNOWN and is_array(t) for t in types):
            self.error("Nested arrays are not supported", line)
            return UNKNOWN

        if expected is not None and is_array(expected) and expected != UNKNOWN:
            want = element_type(expected)
            for i, t in enumerate(types):
                if not compatible(want, t):
                    self.error(f"Array element {i} has type '{t}', expected '{want}'", line)
            return expected

        known = [t for t in types if t != UNKNOWN]
        if not types:
            return EMPTY_ARRAY
        if len(known) != len(types) or not known:
            return UNKNOWN
        if len(set(known)) == 1:
            return f"{known[0]}[]"
        if all(t in NUMERIC for t in known):
            return "float[]"
        self.error("Array elements must all have the same type", line)
        return UNKNOWN

    def visit_ArrayAccessNode(self, node):
        array_type = self.visit(node.array)
        index_type = self.visit(node.index)
        if index_type not in ("int", UNKNOWN):
            self.error(f"Array index must be of type 'int', got '{index_type}'", node.line)
        if array_type == UNKNOWN:
            return UNKNOWN
        if not is_array(array_type):
            self.error(f"Cannot index a value of type '{array_type}'", node.line)
            return UNKNOWN
        return element_type(array_type)

    def visit_UnaryOpNode(self, node):
        t = self.visit(node.operand)
        if t == UNKNOWN:
            return UNKNOWN
        if node.op == "-" and t in NUMERIC:
            return t
        if node.op == "!" and t == "bool":
            return "bool"
        self.error(f"Operator '{node.op}' cannot be applied to type '{t}'", node.line)
        return UNKNOWN

    def visit_BinOpNode(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op, line = node.op, node.line
        unknown = UNKNOWN in (left, right)

        if op in ARITHMETIC_OPS:
            if unknown:
                return UNKNOWN
            if op == "+" and left == "string" and right == "string":
                return "string"
            if op == "+" and "string" in (left, right):
                self.error(f"Cannot concatenate '{left}' and '{right}': '+' joins two strings only", line)
                return UNKNOWN
            if left in NUMERIC and right in NUMERIC:
                return "int" if left == right == "int" else "float"
            self.error(f"Operator '{op}' cannot be applied to '{left}' and '{right}'", line)
            return UNKNOWN

        if op in ORDERING_OPS:
            both_numeric = left in NUMERIC and right in NUMERIC
            if not unknown and not both_numeric and not (left == right == "string"):
                self.error(f"Operator '{op}' cannot compare '{left}' with '{right}'", line)
            return "bool"

        if op in EQUALITY_OPS:
            if not unknown and not (compatible(left, right) or compatible(right, left)):
                self.error(f"Operator '{op}' cannot compare '{left}' with '{right}'", line)
            return "bool"

        if op in LOGICAL_OPS:
            if not unknown and not (left == right == "bool"):
                self.error(f"Operator '{op}' requires 'bool' operands, got '{left}' and '{right}'", line)
            return "bool"

        self.error(f"Unknown operator '{op}'", line)
        return UNKNOWN

    def visit_FunctionCallNode(self, node):
        line = node.line
        symbol = self.current_scope.lookup(node.name)

        if symbol is None or symbol.kind != "function":
            for arg in node.args:
                self.visit(arg)
            if symbol is None:
                self.error(f"Undeclared function '{node.name}'", line)
            else:
                self.error(f"'{node.name}' is not a function", line)
            return UNKNOWN

        if node.name == "print":
            for arg in node.args:
                self.visit(arg)
            return "void"

        params = symbol.extra.get("params", [])
        if len(params) != len(node.args):
            self.error(f"Function '{node.name}' expects {len(params)} arguments, but {len(node.args)} were provided", line)

        for i, arg in enumerate(node.args):
            expected = params[i][1] if i < len(params) else None
            actual = self._expr(arg, self._hint(expected))
            if expected is not None and not compatible(expected, actual):
                self.error(f"Argument {i + 1} of '{node.name}' expects '{expected}', got '{actual}'", line)

        return symbol.symbol_type

    def visit_MethodCallNode(self, node):
        target_type = self.visit(node.target)
        for arg in node.args:
            self.visit(arg)
        if target_type == UNKNOWN:
            return UNKNOWN

        if node.method_name == "length":
            if not (is_array(target_type) or target_type == "string"):
                self.error(f"Type '{target_type}' has no method 'length'", node.line)
                return UNKNOWN
            if node.args:
                self.error("Method 'length' takes no arguments", node.line)
            return "int"

        self.error(f"Type '{target_type}' has no method '{node.method_name}'", node.line)
        return UNKNOWN
