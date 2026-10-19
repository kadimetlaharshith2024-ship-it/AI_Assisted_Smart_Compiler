import pytest

from app.core.lexer import build_lexer
from app.core.parser import parse_code


def tokens(code):
    lexer = build_lexer()
    lexer.input(code)
    return [(t.type, t.value) for t in lexer], lexer.errors


def parse(code):
    tree, lex_errors, parse_errors = parse_code(code)
    return tree, lex_errors + parse_errors


def expr(code):
    """AST of the expression in `print(<code>);`"""
    tree, errors = parse(f"print({code});")
    assert errors == [], errors
    return tree.statements[0].expression


# ---- lexer ----

def test_keywords_identifiers_and_literals():
    toks, errors = tokens('let x1: float = 3.5; print("hi");')
    assert errors == []
    assert [t for t, _ in toks][:6] == ["LET", "IDENTIFIER", "COLON", "TYPE_FLOAT", "ASSIGN", "FLOAT_LITERAL"]
    assert ("STRING_LITERAL", "hi") in toks

def test_int_and_float_literals_are_numbers():
    toks, _ = tokens("42 3.14")
    assert toks == [("INT_LITERAL", 42), ("FLOAT_LITERAL", 3.14)]

def test_keywords_are_not_identifiers():
    toks, _ = tokens("let letter")
    assert [t for t, _ in toks] == ["LET", "IDENTIFIER"]

def test_comments_are_ignored_and_lines_still_counted():
    lexer = build_lexer()
    lexer.input("// note\n/* a\nb */ let x")
    toks = list(lexer)
    assert [t.type for t in toks] == ["LET", "IDENTIFIER"]
    assert toks[0].lineno == 3

def test_illegal_character_is_reported_with_its_line():
    _, errors = tokens("let a: int = 1;\nlet b: int = 2 @ 3;")
    assert len(errors) == 1 and errors[0]["line"] == 2 and "'@'" in errors[0]["message"]

def test_multi_character_operators():
    toks, _ = tokens("== != <= >= && || ->")
    assert [t for t, _ in toks] == ["EQ", "NEQ", "LE", "GE", "AND", "OR", "ARROW"]


# ---- parser: structure ----

def test_empty_program():
    tree, errors = parse("")
    assert errors == [] and tree.statements == []

def test_multiplication_binds_tighter_than_addition():
    node = expr("1 + 2 * 3")
    assert node.op == "+" and node.right.op == "*"

def test_subtraction_is_left_associative():
    node = expr("10 - 3 - 2")
    assert node.op == "-" and node.left.op == "-" and node.right.value == 2

def test_parentheses_override_precedence():
    node = expr("(1 + 2) * 3")
    assert node.op == "*" and node.left.op == "+"

def test_logical_precedence():
    node = expr("true || false && false")
    assert node.op == "||" and node.right.op == "&&"

def test_if_else_if_else_chain():
    tree, errors = parse("if (a) { } else if (b) { } else if (c) { } else { }")
    node = tree.statements[0]
    assert errors == [] and len(node.elif_branches) == 2 and node.else_branch is not None

def test_function_declaration_shape():
    tree, errors = parse("fn add(a: int, b: int) -> int { return a + b; }")
    fn = tree.statements[0]
    assert errors == [] and fn.name == "add" and fn.params == [("a", "int"), ("b", "int")] and fn.return_type == "int"

def test_array_literal_index_and_assignment():
    tree, errors = parse("let a: int[] = [1, 2]; a[0] = 5; print(a[1]);")
    assert errors == [] and type(tree.statements[1]).__name__ == "AssignNode"

def test_method_call_node():
    node = expr("a.length()")
    assert type(node).__name__ == "MethodCallNode" and node.method_name == "length"

def test_for_loop_with_empty_clauses():
    tree, errors = parse("for (;;) { break; }")
    assert errors == []
    assert tree.statements[0].condition is None and tree.statements[0].update is None

def test_node_lines_follow_the_source():
    tree, _ = parse("let a: int = 1;\n\nlet b: int = 2;")
    assert [s.line for s in tree.statements] == [1, 3]


# ---- parser: syntax errors ----

@pytest.mark.parametrize("code", [
    "let a: int = 10",                 # missing semicolon
    "let x = 5;",                      # missing type annotation
    "let a: int = ;",                  # missing expression
    "if (true) { print(1);",           # unclosed brace
    "fn f() { }",                      # missing -> return type
    "print(1 +);",                     # dangling operator
    "while true { }",                  # missing parentheses
    "1 < 2 < 3;",                      # comparisons don't chain
    "let a: int[ = [1];",              # broken array type
])
def test_syntax_errors_are_reported(code):
    _, errors = parse(code)
    assert errors, f"expected a syntax error for: {code}"

def test_syntax_error_reports_the_offending_line():
    _, errors = parse("let a: int = 1;\nlet b: int = 2;\nlet c: int = ;")
    assert errors[0]["line"] == 3 and errors[0]["message"].startswith("Syntax error")

def test_unexpected_end_of_input():
    _, errors = parse("fn f() -> void {")
    assert any(e["message"] == "Unexpected end of input" for e in errors)

def test_parse_errors_do_not_leak_between_calls():
    parse("let a: int = ;")
    _, errors = parse("let a: int = 1;")
    assert errors == []
