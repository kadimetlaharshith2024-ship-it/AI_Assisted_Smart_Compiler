"""
Tree-walking interpreter for the Lumen AST.

Runs a program that has already passed the type checker and returns the
printed output lines. Because the programs come from a public playground, the
interpreter enforces a set of resource limits (steps, wall-clock time, call
depth, output size) so a bad program ends with a clear runtime error instead
of hanging or flooding the server.
"""
import math
import sys
import time

DEFAULT_MAX_STEPS = 1_000_000        # statements + loop iterations + calls
DEFAULT_MAX_SECONDS = 3.0            # wall-clock budget for one run
DEFAULT_MAX_CALL_DEPTH = 200         # nested Lumen function calls
DEFAULT_MAX_OUTPUT_LINES = 5_000     # lines printed by one run
PYTHON_RECURSION_LIMIT = 5_000       # headroom for MAX_CALL_DEPTH nested calls


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


class LumenArray(list):
    """A Lumen array. Remembers its element type so that storing an int into
    a `float[]` keeps the value a float (a[0] = 1 stores 1.0)."""

    def __init__(self, items=(), elem_type=None):
        super().__init__(items)
        self.elem_type = elem_type


def coerce(value, type_name):
    """Apply Lumen's one implicit conversion: int -> float (also inside float[])."""
    if type_name == "float":
        if isinstance(value, int) and not isinstance(value, bool):
            return float(value)
        return value
    if type_name and type_name.endswith("[]") and isinstance(value, list):
        elem = type_name[:-2]
        if isinstance(value, LumenArray) and value.elem_type == elem:
            return value  # already typed: keep the same object (arrays are references)
        return LumenArray([coerce(v, elem) for v in value], elem)
    return value


def int_div(left, right):
    """C-style integer division: truncates toward zero (-7 / 2 == -3)."""
    quotient = abs(left) // abs(right)
    return quotient if (left < 0) == (right < 0) else -quotient


class Environment:
    def __init__(self, parent=None):
        self.vars = {}
        self.types = {}
        self.parent = parent

    def define(self, name, value, type_name=None):
        self.vars[name] = coerce(value, type_name)
        self.types[name] = type_name

    def get(self, name):
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise LumenRuntimeError(f"Undefined variable '{name}'")

    def set(self, name, value):
        env = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = coerce(value, env.types.get(name))
                return
            env = env.parent
        raise LumenRuntimeError(f"Undefined variable '{name}'")


class Interpreter:
    def __init__(self, max_steps=DEFAULT_MAX_STEPS, max_seconds=DEFAULT_MAX_SECONDS,
                 max_call_depth=DEFAULT_MAX_CALL_DEPTH, max_output_lines=DEFAULT_MAX_OUTPUT_LINES):
        self.global_env = Environment()
        self.functions = {}
        self.output = []

        self.max_steps = max_steps
        self.max_seconds = max_seconds
        self.max_call_depth = max_call_depth
        self.max_output_lines = max_output_lines

        self.steps = 0
        self.depth = 0
        self.deadline = None

    def run(self, program_node):
        """Execute a ProgramNode. Returns the list of printed output lines."""
        self.deadline = time.monotonic() + self.max_seconds
        if sys.getrecursionlimit() < PYTHON_RECURSION_LIMIT:
            sys.setrecursionlimit(PYTHON_RECURSION_LIMIT)

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
            where = f", line {e.line}" if e.line else ""
            self.output.append(f"[Runtime Error{where}] {e.message}")
        except (ReturnSignal, BreakSignal, ContinueSignal):
            pass  # stray control-flow signal; the type checker normally rejects these
        except RecursionError:
            self.output.append("[Runtime Error] Maximum recursion depth exceeded (possible infinite recursion)")
        except Exception as e:  # never lose the output produced so far
            self.output.append(f"[Runtime Error] {e}")

        return self.output

    # ---- resource limits ----

    def _tick(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise LumenRuntimeError("Execution step limit exceeded (possible infinite loop)")
        if self.steps & 0x3FF == 0 and time.monotonic() > self.deadline:
            raise LumenRuntimeError(f"Execution time limit of {self.max_seconds:g}s exceeded (possible infinite loop)")

    def _emit(self, text):
        if len(self.output) >= self.max_output_lines:
            raise LumenRuntimeError(f"Output limit of {self.max_output_lines} lines exceeded")
        self.output.append(text)

    # ---- statements ----

    def exec_stmt(self, node, env):
        self._tick()
        method = getattr(self, f"exec_{type(node).__name__}", None)
        try:
            if method is None:
                # Bare expression statement (e.g. a function call used as a statement)
                self.eval_expr(node, env)
            else:
                method(node, env)
        except LumenRuntimeError as e:
            if not e.line:
                e.line = getattr(node, "line", 0)
            raise

    def exec_VarDeclNode(self, node, env):
        if node.value is not None:
            value = self.eval_expr(node.value, env)
        else:
            value = self._default_value(node.var_type)
        env.define(node.name, value, node.var_type)

    def exec_AssignNode(self, node, env):
        value = self.eval_expr(node.value, env)
        target = node.target
        if type(target).__name__ == "IdentifierNode":
            env.set(target.name, value)
        elif type(target).__name__ == "ArrayAccessNode":
            arr = self.eval_expr(target.array, env)
            idx = self.eval_expr(target.index, env)
            self._check_index(arr, idx, node.line)
            arr[idx] = coerce(value, getattr(arr, "elem_type", None))
        else:
            raise LumenRuntimeError("Invalid assignment target", node.line)

    def exec_PrintNode(self, node, env):
        value = self.eval_expr(node.expression, env) if node.expression is not None else ""
        self._emit(self._stringify(value))

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
        while self.eval_expr(node.condition, env):
            self._tick()
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
        while node.condition is None or self.eval_expr(node.condition, loop_env):
            self._tick()
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
            self._tick()
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
        try:
            return method(node, env)
        except LumenRuntimeError as e:
            if not e.line:
                e.line = getattr(node, "line", 0)
            raise

    def eval_IntLiteralNode(self, node, env):
        return node.value

    def eval_FloatLiteralNode(self, node, env):
        return node.value

    def eval_BoolLiteralNode(self, node, env):
        return node.value

    def eval_StringLiteralNode(self, node, env):
        return node.value

    def eval_ArrayLiteralNode(self, node, env):
        return LumenArray([self.eval_expr(el, env) for el in node.elements])

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
        op = node.op

        # Short-circuit: the right side must not run when the left decides the result.
        if op == "&&":
            return bool(self.eval_expr(node.left, env)) and bool(self.eval_expr(node.right, env))
        if op == "||":
            return bool(self.eval_expr(node.left, env)) or bool(self.eval_expr(node.right, env))

        left = self.eval_expr(node.left, env)
        right = self.eval_expr(node.right, env)
        both_int = isinstance(left, int) and isinstance(right, int)
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
                return int_div(left, right) if both_int else left / right
            if op == "%":
                if right == 0:
                    raise LumenRuntimeError("Modulo by zero", node.line)
                return left - right * int_div(left, right) if both_int else math.fmod(left, right)
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
            self._emit(self._stringify(value))
            return None

        func = self.functions.get(node.name)
        if func is None:
            raise LumenRuntimeError(f"Undefined function '{node.name}'", node.line)
        if len(func.params) != len(node.args):
            raise LumenRuntimeError(
                f"Function '{node.name}' expects {len(func.params)} arguments, but {len(node.args)} were provided", node.line)

        self._tick()
        if self.depth >= self.max_call_depth:
            raise LumenRuntimeError(
                f"Maximum call depth ({self.max_call_depth}) exceeded (possible infinite recursion)", node.line)

        call_env = Environment(parent=self.global_env)
        for (param_name, param_type), arg_node in zip(func.params, node.args):
            call_env.define(param_name, self.eval_expr(arg_node, env), param_type)

        self.depth += 1
        try:
            self._exec_block(func.body, call_env)
        except ReturnSignal as r:
            return coerce(r.value, func.return_type)
        finally:
            self.depth -= 1
        return None

    def eval_MethodCallNode(self, node, env):
        target = self.eval_expr(node.target, env)
        if node.method_name == "length":
            if isinstance(target, (list, str)):
                return len(target)
            raise LumenRuntimeError("'length' can only be called on an array or a string", node.line)
        raise LumenRuntimeError(f"Unknown method '{node.method_name}'", node.line)

    # ---- helpers ----

    def _check_index(self, arr, idx, line):
        if not isinstance(arr, list):
            raise LumenRuntimeError("Cannot index a non-array value", line)
        if not isinstance(idx, int) or idx < 0 or idx >= len(arr):
            raise LumenRuntimeError(f"Array index {idx} out of bounds (length {len(arr)})", line)

    def _default_value(self, var_type):
        if var_type.endswith("[]"):
            return LumenArray([], var_type[:-2])
        return {"int": 0, "float": 0.0, "bool": False, "string": ""}.get(var_type, None)

    def _stringify(self, value):
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, list):
            return "[" + ", ".join(self._stringify(v) for v in value) + "]"
        return str(value)


def run_program(program_node, **limits):
    """Execute an AST and return printed output lines.

    `limits` may override max_steps, max_seconds, max_call_depth and
    max_output_lines (mainly useful in tests)."""
    return Interpreter(**limits).run(program_node)
