import pytest
from app.core.parser import parse_code
from app.semantic.type_checker import TypeChecker
from app.core.interpreter import run_program


def run(code, **limits):
    tree, lex_errors, parse_errors = parse_code(code)
    assert not lex_errors and not parse_errors, (lex_errors, parse_errors)
    errors = TypeChecker().visit(tree)
    assert errors == [], errors
    return run_program(tree, **limits)


# ---- .length() ----

def test_array_length():
    assert run('let n: int[] = [1, 2, 3]; print(n.length());') == ["3"]

def test_string_length():
    assert run('print("hello".length());') == ["5"]

def test_handbook_arrays_example():
    code = '''let nums: int[] = [1, 2, 3, 4, 5];
print(nums[0]);
nums[1] = 99;
print(nums[1]);
print(nums.length());'''
    assert run(code) == ["1", "99", "5"]

def test_handbook_variables_example():
    code = '''let age: int = 25;
let price: float = 9.99;
let isOpen: bool = true;
let city: string = "Chennai";
let scores: int[] = [90, 85, 77];
print(age); print(price); print(isOpen); print(city); print(scores.length());'''
    assert run(code) == ["25", "9.99", "true", "Chennai", "3"]

def test_handbook_factorial_example():
    code = '''fn factorial(n: int) -> int {
    if (n <= 1) { return 1; }
    return n * factorial(n - 1);
}
fn main() -> void {
    let limit: int = 6;
    for (let i: int = 1; i <= limit; i = i + 1) { print(factorial(i)); }
}
main();'''
    assert run(code) == ["1", "2", "6", "24", "120", "720"]


# ---- int -> float conversion ----

def test_float_declaration_from_int():
    assert run('let f: float = 3; print(f);') == ["3.0"]

def test_float_assignment_from_int():
    assert run('let f: float = 1.5; f = 2; print(f);') == ["2.0"]

def test_float_array_literal_and_element_assignment():
    assert run('let a: float[] = [1, 2]; a[0] = 7; print(a);') == ["[7.0, 2.0]"]

def test_float_parameter_and_return():
    code = 'fn half(x: float) -> float { return x / 2; } fn one() -> float { return 1; } print(half(3)); print(one());'
    assert run(code) == ["1.5", "1.0"]

def test_float_default_value():
    assert run('let f: float; print(f);') == ["0.0"]

def test_int_arrays_stay_int():
    assert run('let a: int[] = [1, 2]; a[0] = 5; print(a);') == ["[5, 2]"]


# ---- arithmetic semantics ----

@pytest.mark.parametrize("expr, expected", [
    ("7 / 2", "3"), ("-7 / 2", "-3"), ("7 / -2", "-3"), ("-7 / -2", "3"),
    ("7 % 3", "1"), ("-7 % 3", "-1"), ("7 % -3", "1"), ("-7 % -3", "-1"),
    ("7.5 / 2", "3.75"), ("7.5 % 2", "1.5"),
    ("10 / 3 * 3 + 10 % 3", "10"),
])
def test_c_style_division_and_modulo(expr, expected):
    assert run(f"print({expr});") == [expected]

def test_big_integer_division_is_exact():
    assert run("print(9007199254740993 / 1);") == ["9007199254740993"]

@pytest.mark.parametrize("expr, message", [
    ("1 / 0", "Division by zero"), ("1.5 / 0", "Division by zero"), ("1 % 0", "Modulo by zero"),
])
def test_division_by_zero(expr, message):
    out = run(f"print({expr});")
    assert out == [f"[Runtime Error, line 1] {message}"]

def test_logical_operators_short_circuit():
    code = '''let a: int[] = [1];
let i: int = 5;
if (i < a.length() && a[i] > 0) { print("no"); } else { print("safe"); }
if (true || a[9] > 0) { print("or-safe"); }'''
    assert run(code) == ["safe", "or-safe"]


# ---- runtime errors: line numbers and partial output ----

def test_runtime_error_has_line_and_keeps_earlier_output():
    code = 'print(1);\nlet a: int[] = [1];\nprint(a[3]);\nprint(2);'
    assert run(code) == ["1", "[Runtime Error, line 3] Array index 3 out of bounds (length 1)"]

def test_division_error_line_inside_function():
    code = 'fn f(a: int) -> int {\n  return 10 / a;\n}\nprint(f(0));'
    assert run(code) == ["[Runtime Error, line 2] Division by zero"]

def test_runtime_error_inside_loop_reports_its_line():
    code = 'let a: int[] = [1, 2];\nfor (let i: int = 0; i < 5; i = i + 1) {\n  print(a[i]);\n}'
    assert run(code) == ["1", "2", "[Runtime Error, line 3] Array index 2 out of bounds (length 2)"]


# ---- resource limits ----

def test_infinite_loop_hits_step_limit():
    out = run("while (true) { }", max_steps=10_000)
    assert len(out) == 1 and "step limit" in out[0]

def test_nested_loops_share_one_budget():
    code = '''for (let i: int = 0; i < 100000; i = i + 1) {
  for (let j: int = 0; j < 100000; j = j + 1) { }
}'''
    out = run(code, max_steps=50_000)
    assert len(out) == 1 and "step limit" in out[0]

def test_time_limit():
    out = run("while (true) { }", max_steps=10**12, max_seconds=0.05)
    assert len(out) == 1 and "time limit" in out[0]

def test_infinite_recursion_is_reported_clearly():
    out = run("fn f(n: int) -> int { return f(n + 1); } print(f(1));")
    assert out == ["[Runtime Error, line 1] Maximum call depth (200) exceeded (possible infinite recursion)"]

def test_reasonable_recursion_depth_works():
    code = "fn s(n: int) -> int { if (n == 0) { return 0; } return n + s(n - 1); } print(s(150));"
    assert run(code) == ["11325"]

def test_output_limit():
    out = run('while (true) { print(1); }', max_output_lines=10)
    assert len(out) == 11 and "Output limit" in out[-1]

def test_loops_longer_than_old_100k_cap_now_work():
    code = "let t: int = 0; for (let i: int = 0; i < 150000; i = i + 1) { t = t + 1; } print(t);"
    assert run(code) == ["150000"]
