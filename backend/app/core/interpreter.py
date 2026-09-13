"""
Minimal tree-walking interpreter for the Lumen AST.

This exists to give the "Execution" stage of the pipeline something real to
call (previously: nothing after semantic analysis). It intentionally covers
the language constructs already handled by the parser/type-checker and
nothing more exotic — the goal is a working demo, not an optimizing runtime.
"""

MAX_LOOP_ITERATIONS = 100_000  # guard against infinite loops during a demo


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class LumenRuntimeError(Exception):
    def __init__(self, message, line=0):
        self.message = message
        self.line = line
        super().__init__(message)


class Environment:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def define(self, name, value):
        self.vars[name] = value

    def get(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name)
        raise LumenRuntimeError(f"Undefined variable '{name}'")

    def set(self, name, value):
        if name in self.vars:
            self.vars[name] = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        # Fall back to defining in the current scope (shouldn't normally
        # happen since the semantic checker validates declarations first).
        self.vars[name] = value


class Interpreter:
    def __init__(self):
        self.global_env = Environment()
        self.functions = {}
        self.output = []

    def run(self, program_node):
        """Execute a ProgramNode. Returns the list of printed output lines."""
        try:
            statements = getattr(program_node, "statements", [])

            # Pre-register functions so calls can appear before declarations.
            for stmt in statements:
                if type(stmt).__name__ == "FunctionDeclNode":
                    self.functions[stmt.name] = stmt

            for stmt in statements:
                if type(stmt).__name__ != "FunctionDeclNode":
                    self.exec_stmt(stmt, self.global_env)

        except LumenRuntimeError as e:
            self.output.append(f"[Runtime Error, line {e.line}] {e.message}")
        except ReturnSignal:
            pass  # top-level `return` — ignore
        except RecursionError:
            self.output.append("[Runtime Error] Maximum recursion depth exceeded (possible infinite recursion)")

        return self.output

    # ---- statements ----

    def exec_stmt(self, node, env):
        method = getattr(self, f"exec_{type(node).__name__}", None)
        if method is None:
            # Bare expression statement (e.g. a function call used as a statement)
            self.eval_expr(node, env)
            return
        method(node, env)

    def exec_VarDeclNode(self, node, env):
        value = self.eval_expr(node.value, env) if node.value is not None else self._default_value(node.var_type)
        env.define(node.name, value)

    def exec_AssignNode(self, node, env):
        value = self.eval_expr(node.value, env)
        target = node.target
        if type(target).__name__ == "IdentifierNode":
            env.set(target.name, value)
        elif type(target).__name__ == "ArrayAccessNode":
            arr = self.eval_expr(target.array, env)
            idx = self.eval_expr(target.index, env)
            self._check_index(arr, idx, node.line)
            arr[idx] = value
        else:
            raise LumenRuntimeError("Invalid assignment target", node.line)

    def exec_PrintNode(self, node, env):
        value = self.eval_expr(node.expression, env) if node.expression is not None else ""
        self.output.append(self._stringify(value))

    def exec_IfNode(self, node, env):
        if self.eval_expr(node.condition, env):
            self._exec_block(node.then_branch, env)
            return
        for cond, block in getattr(node, "elif_branches", []) or []:
            if self.eval_expr(cond, env):
                self._exec_block(block, env)
                return
        if getattr(node, "else_branch", None):
            self._exec_block(node.else_branch, env)

    def exec_WhileNode(self, node, env):
        iterations = 0
        while self.eval_expr(node.condition, env):
            iterations += 1
            if iterations > MAX_LOOP_ITERATIONS:
                raise LumenRuntimeError("Loop exceeded maximum iteration limit (possible infinite loop)", node.line)
            try:
                self._exec_block(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_ForNode(self, node, env):
        loop_env = Environment(parent=env)
        if node.init is not None:
            self.exec_stmt(node.init, loop_env)
        iterations = 0
        while node.condition is None or self.eval_expr(node.condition, loop_env):
            iterations += 1
            if iterations > MAX_LOOP_ITERATIONS:
                raise LumenRuntimeError("Loop exceeded maximum iteration limit (possible infinite loop)", node.line)
            try:
                self._exec_block(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                pass
            if node.update is not None:
                self.exec_stmt(node.update, loop_env)

    def exec_ForEachNode(self, node, env):
        iterable = self.eval_expr(node.iterable, env)
        if not isinstance(iterable, list):
            raise LumenRuntimeError("foreach target is not an array", node.line)
        for item in iterable:
            loop_env = Environment(parent=env)
            loop_env.define(node.item_name, item)
            try:
                self._exec_block(node.body, loop_env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_BreakNode(self, node, env):
        raise BreakSignal()

    def exec_ContinueNode(self, node, env):
        raise ContinueSignal()

    def exec_ReturnNode(self, node, env):
        value = self.eval_expr(node.expression, env) if node.expression is not None else None
        raise ReturnSignal(value)

    def exec_BlockNode(self, node, env):
        self._exec_block(node, env)

    def _exec_block(self, block, parent_env):
        block_env = Environment(parent=parent_env)
        for stmt in getattr(block, "statements", []):
            self.exec_stmt(stmt, block_env)

    # ---- expressions ----

    def eval_expr(self, node, env):
        if node is None:
            return None
        method = getattr(self, f"eval_{type(node).__name__}", None)
        if method is None:
            raise LumenRuntimeError(f"Cannot evaluate node type '{type(node).__name__}'", getattr(node, "line", 0))
        return method(node, env)

    def eval_IntLiteralNode(self, node, env):
        return node.value

    def eval_FloatLiteralNode(self, node, env):
        return node.value

    def eval_BoolLiteralNode(self, node, env):
        return node.value

    def eval_StringLiteralNode(self, node, env):
        return node.value

    def eval_ArrayLiteralNode(self, node, env):
        return [self.eval_expr(el, env) for el in node.elements]

    def eval_IdentifierNode(self, node, env):
        return env.get(node.name)

    def eval_ArrayAccessNode(self, node, env):
        arr = self.eval_expr(node.array, env)
        idx = self.eval_expr(node.index, env)
        self._check_index(arr, idx, node.line)
        return arr[idx]

    def eval_UnaryOpNode(self, node, env):
        value = self.eval_expr(node.operand, env)
        if node.op == "-":
            return -value
        if node.op == "!":
            return not value
        raise LumenRuntimeError(f"Unknown unary operator '{node.op}'", node.line)

    def eval_BinOpNode(self, node, env):
        left = self.eval_expr(node.left, env)
        right = self.eval_expr(node.right, env)
        op = node.op
        try:
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                if right == 0:
                    raise LumenRuntimeError("Division by zero", node.line)
                result = left / right
                return int(result) if isinstance(left, int) and isinstance(right, int) else result
            if op == "%":
                return left % right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == "<":
                return left < right
            if op == ">":
                return left > right
            if op == "<=":
                return left <= right
            if op == ">=":
                return left >= right
            if op == "&&":
                return bool(left) and bool(right)
            if op == "||":
                return bool(left) or bool(right)
        except LumenRuntimeError:
            raise
        except Exception as e:
            raise LumenRuntimeError(f"Invalid operation '{op}': {e}", node.line)
        raise LumenRuntimeError(f"Unknown operator '{op}'", node.line)

    def eval_FunctionCallNode(self, node, env):
        if node.name == "print":
            # Defensive: grammar routes `print(...)` through PrintNode, but
            # guard against it being reached as a call expression too.
            value = self.eval_expr(node.args[0], env) if node.args else ""
            self.output.append(self._stringify(value))
            return None

        func = self.functions.get(node.name)
        if func is None:
            raise LumenRuntimeError(f"Undefined function '{node.name}'", node.line)

        call_env = Environment(parent=self.global_env)
        for (param_name, _param_type), arg_node in zip(func.params, node.args):
            call_env.define(param_name, self.eval_expr(arg_node, env))

        try:
            self._exec_block(func.body, call_env)
        except ReturnSignal as r:
            return r.value
        return None

    # ---- helpers ----

    def _check_index(self, arr, idx, line):
        if not isinstance(arr, list):
            raise LumenRuntimeError("Cannot index a non-array value", line)
        if not isinstance(idx, int) or idx < 0 or idx >= len(arr):
            raise LumenRuntimeError(f"Array index {idx} out of bounds", line)

    def _default_value(self, var_type):
        return {
            "int": 0, "float": 0.0, "bool": False, "string": "",
        }.get(var_type, None)

    def _stringify(self, value):
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, list):
            return "[" + ", ".join(self._stringify(v) for v in value) + "]"
        return str(value)


def run_program(program_node):
    """Convenience entry point: execute an AST and return printed output lines."""
    interpreter = Interpreter()
    return interpreter.run(program_node)
