from app.semantic.visitor import NodeVisitor
from app.semantic.symbol_table import SymbolTable, Symbol

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
        
        # Register built-ins
        self.global_scope.define("print", Symbol("print", "function", kind="function"))

    def error(self, message, line=0):
        err = {"line": line, "message": message}
        self.errors.append(err)

    def visit(self, node, *args, **kwargs):
        if node is None:
            return None
        node_type = type(node).__name__
        method_name = f'visit_{node_type}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node, *args, **kwargs)

    def visit_ProgramNode(self, node):
        statements = getattr(node, 'statements', [])
        
        # Pass 1: Pre-register all top-level functions for recursion & forward references
        for stmt in statements:
            if isinstance(stmt, tuple) and type(stmt).__name__ == 'FunctionDeclNode':
                pass
            elif type(stmt).__name__ == 'FunctionDeclNode':
                func_symbol = Symbol(stmt.name, stmt.return_type, kind="function", extra={"params": stmt.params})
                self.current_scope.define(stmt.name, func_symbol)

        # Pass 2: Type check statements
        for stmt in statements:
            self.visit(stmt)
            
        return self.errors

    def visit_FunctionDeclNode(self, node):
        func_symbol = Symbol(node.name, node.return_type, kind="function", extra={"params": node.params})
        
        prev_scope = self.current_scope
        self.current_scope = SymbolTable(parent=prev_scope)
        self.current_function = node

        # Register parameters
        for param in node.params:
            param_name = param[0] if isinstance(param, (list, tuple)) else getattr(param, 'name', str(param))
            param_type = param[1] if isinstance(param, (list, tuple)) and len(param) > 1 else 'int'
            param_symbol = Symbol(param_name, param_type, kind="variable")
            self.current_scope.define(param_name, param_symbol)

        # Visit body block statements
        body_block = node.body
        if hasattr(body_block, 'statements'):
            for stmt in body_block.statements:
                self.visit(stmt)

        self.current_scope = prev_scope
        self.current_function = None

    def visit_VarDeclNode(self, node):
        var_type = getattr(node, 'var_type', 'int')
        if hasattr(node, 'value') and node.value is not None:
            self.visit(node.value)
        
        var_symbol = Symbol(node.name, var_type, kind="variable")
        if not self.current_scope.define(node.name, var_symbol):
            self.error(f"Variable '{node.name}' is already declared in this scope", getattr(node, 'line', 0))

    def visit_AssignNode(self, node):
        if hasattr(node, 'target'):
            self.visit(node.target)
        if hasattr(node, 'value'):
            self.visit(node.value)

    def visit_IdentifierNode(self, node):
        symbol = self.current_scope.lookup(node.name)
        if not symbol:
            self.error(f"Undeclared identifier '{node.name}'", getattr(node, 'line', 0))
            return "unknown"
        return symbol.symbol_type

    def visit_BinOpNode(self, node):
        left_type = self.visit(node.left) if hasattr(node, 'left') else "int"
        right_type = self.visit(node.right) if hasattr(node, 'right') else "int"
        
        op = getattr(node, 'op', '+')
        line = getattr(node, 'line', 0)

        # Basic type compatibility for arithmetic operators (+, -, *, /, %)
        if op in ['+', '-', '*', '/', '%']:
            if left_type == "string" or right_type == "string":
                if op == '+' and (left_type == "string" or right_type == "string"):
                    return "string"  # String concatenation is allowed in Lumen
                else:
                    self.error(f"Invalid operation '{op}' between types '{left_type}' and '{right_type}'", line)
                    return "int"
            if left_type == "bool" or right_type == "bool":
                self.error(f"Type mismatch: cannot perform arithmetic operation '{op}' on boolean types", line)
                return "int"
            return "int" if left_type == "int" and right_type == "int" else "float"

        # Comparison and logical operators always return bool
        return "bool"

    def visit_UnaryOpNode(self, node):
        if hasattr(node, 'operand'):
            self.visit(node.operand)
        return "int"

    def visit_IntLiteralNode(self, node):
        return "int"

    def visit_FloatLiteralNode(self, node):
        return "float"

    def visit_StringLiteralNode(self, node):
        return "string"

    def visit_BoolLiteralNode(self, node):
        return "bool"

    def visit_ArrayLiteralNode(self, node):
        if hasattr(node, 'elements'):
            for el in node.elements:
                self.visit(el)
        return "int[]"

    def visit_FunctionCallNode(self, node):
        symbol = self.current_scope.lookup(node.name)
        line = getattr(node, 'line', 0)
        
        if not symbol:
            self.error(f"Undeclared function '{node.name}'", line)
            return "int"

        # Validate arguments if parameter metadata exists
        expected_params = symbol.extra.get("params", [])
        provided_args = getattr(node, 'args', [])

        if len(expected_params) != len(provided_args):
            self.error(f"Function '{node.name}' expects {len(expected_params)} arguments, but {len(provided_args)} were provided", line)

        for arg in provided_args:
            self.visit(arg)

        return symbol.symbol_type

    def visit_PrintNode(self, node):
        if hasattr(node, 'expression') and node.expression:
            self.visit(node.expression)

    def visit_IfNode(self, node):
        if hasattr(node, 'condition'):
            self.visit(node.condition)
        if hasattr(node, 'then_branch') and hasattr(node.then_branch, 'statements'):
            for stmt in node.then_branch.statements:
                self.visit(stmt)
        if hasattr(node, 'else_branch') and node.else_branch:
            if hasattr(node.else_branch, 'statements'):
                for stmt in node.else_branch.statements:
                    self.visit(stmt)

    def visit_WhileNode(self, node):
        if hasattr(node, 'condition'):
            self.visit(node.condition)
        if hasattr(node, 'body') and hasattr(node.body, 'statements'):
            for stmt in node.body.statements:
                self.visit(stmt)

    def visit_ForNode(self, node):
        prev_scope = self.current_scope
        self.current_scope = SymbolTable(parent=prev_scope)
        if hasattr(node, 'init') and node.init:
            self.visit(node.init)
        if hasattr(node, 'condition') and node.condition:
            self.visit(node.condition)
        if hasattr(node, 'update') and node.update:
            self.visit(node.update)
        if hasattr(node, 'body') and hasattr(node.body, 'statements'):
            for stmt in node.body.statements:
                self.visit(stmt)
        self.current_scope = prev_scope

    def visit_ForEachNode(self, node):
        prev_scope = self.current_scope
        self.current_scope = SymbolTable(parent=prev_scope)
        
        if hasattr(node, 'iterable'):
            self.visit(node.iterable)
        
        var_symbol = Symbol(node.item_name, "int", kind="variable")
        self.current_scope.define(node.item_name, var_symbol)
        
        if hasattr(node, 'body') and hasattr(node.body, 'statements'):
            for stmt in node.body.statements:
                self.visit(stmt)
        self.current_scope = prev_scope

    def visit_ReturnNode(self, node):
        if hasattr(node, 'expression') and node.expression:
            self.visit(node.expression)

    def visit_BlockNode(self, node):
        if hasattr(node, 'statements'):
            for stmt in node.statements:
                self.visit(stmt)