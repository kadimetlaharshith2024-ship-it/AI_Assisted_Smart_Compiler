import pytest
from app.services.compiler_service import compile_code_full


def messages(code):
    return [e["message"] for e in compile_code_full(code)["errors"]]


def assert_error(code, fragment):
    msgs = messages(code)
    assert any(fragment in m for m in msgs), f"expected '{fragment}' in {msgs}"


def assert_clean(code):
    assert messages(code) == []


# ---- things that must be rejected ----

@pytest.mark.parametrize("code, fragment", [
    ('let x: int = "hello";', "Cannot initialize 'x'"),
    ('let x: int = 3.5;', "Cannot initialize 'x'"),
    ('let x: int = 1; x = "a";', "Cannot assign a value of type 'string'"),
    ('let a: int[] = [1]; a[0] = "s";', "an array element"),
    ('fn f() -> int { return "s"; }', "must return 'int'"),
    ('fn f() -> void { return 1; }', "cannot return a value"),
    ('fn f() -> int { return; }', "must return a value"),
    ('fn f(a: int) -> int { return a; } let r: int = f("x");', "Argument 1 of 'f'"),
    ('fn f(a: int) -> int { return a; } let r: int = f(1, 2);', "expects 1 arguments"),
    ('if (5) { print(1); }', "must be of type 'bool'"),
    ('while ("yes") { }', "must be of type 'bool'"),
    ('let a: int = 1; if (a == 2) { print(1); } else if (a) { print(2); }', "'else if' condition"),
    ('if (false) { print(1); } else if (true) { print(nope); }', "Undeclared identifier 'nope'"),
    ('print("a" + 1);', "Cannot concatenate"),
    ('print(true + 1);', "cannot be applied"),
    ('print(1 && 2);', "requires 'bool'"),
    ('print(!5);', "cannot be applied to type 'int'"),
    ('print(-"a");', "cannot be applied to type 'string'"),
    ('print(1 == "a");', "cannot compare"),
    ('let a: int[] = [1, "b"];', "Array element 1"),
    ('let a: int = 1; foreach (x in a) { }', "requires an array"),
    ('let s: string[] = ["a"]; let k: int = s[0];', "Cannot initialize 'k'"),
    ('let a: int[] = [1]; print(a["0"]);', "index must be of type 'int'"),
    ('let a: int = 1; print(a[0]);', "Cannot index"),
    ('let a: int = 1; print(a.length());', "has no method 'length'"),
    ('let a: int[] = [1]; print(a.size());', "has no method 'size'"),
    ('break;', "inside a loop"),
    ('continue;', "inside a loop"),
    ('return 1;', "inside a function"),
    ('fn f(a: int) -> int { if (a > 0) { return 1; } }', "on every path"),
    ('fn f() -> void { } let x: int = f();', "Cannot initialize 'x'"),
    ('fn f() -> void { } print(f());', "Cannot print a 'void'"),
    ('fn f() -> void { } fn f() -> void { }', "already declared"),
    ('fn f(a: int, a: int) -> void { }', "Duplicate parameter"),
    ('let x: void;', "cannot have type 'void'"),
    ('if (true) { fn g() -> void { } }', "top level"),
    ('let x: int = 1; let x: int = 2;', "already declared"),
])
def test_rejects(code, fragment):
    assert_error(code, fragment)


# ---- things that must be accepted ----

@pytest.mark.parametrize("code", [
    'let f: float = 3;',
    'let f: float[] = [1, 2.5];',
    'let a: int[] = [];',
    'let n: int[] = [1, 2]; let k: int = n[0] + n.length();',
    'let s: string = "a" + "b"; print(s.length());',
    'fn half(x: float) -> float { return x / 2; } print(half(3));',
    'fn f(a: int) -> int { if (a > 0) { return 1; } else { return 2; } }',
    'fn f(a: int) -> int { if (a > 0) { return 1; } else if (a < 0) { return 2; } else { return 3; } }',
    'if (true) { let q: int = 1; } else { let q: int = 2; }',   # sibling scopes
    'for (let i: int = 0; i < 3; i = i + 1) { let t: int = i; }',
    'let xs: int[] = [1, 2]; foreach (x in xs) { let y: int = x * 2; if (y > 2) { break; } }',
    'let a: bool = 1 < 2 && "a" < "b" || !false;',
    'print("a" == "a"); print(1 == 1.0);',
])
def test_accepts(code):
    assert_clean(code)


def test_no_cascading_errors_after_undeclared_name():
    msgs = messages('let x: int = y + 10;')
    assert msgs == ["Undeclared identifier 'y'"]


def test_errors_are_sorted_by_line():
    code = 'let a: int = "x";\n\nlet b: int = "y";'
    lines = [e["line"] for e in compile_code_full(code)["errors"]]
    assert lines == sorted(lines) and len(lines) == 2
