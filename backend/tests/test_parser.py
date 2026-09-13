import json
from app.core import compile_core

def test_handbook_factorial():
    code = """
    // Compute factorial and print first N results
    fn factorial(n: int) -> int {
        if (n <= 1) {
            return 1;
        }
        return n * factorial(n - 1);
    }

    fn main() -> void {
        let limit: int = 6;
        let results: int[] = [];
        for (let i: int = 1; i <= limit; i = i + 1) {
            let f: int = factorial(i);
            print(f);
        }
    }

    main();
    """
    res = compile_core(code)
    assert len(res["errors"]) == 0, f"Errors: {res['errors']}"
    assert res["ast"] is not None
    assert len(res["tokens"]) > 0
    json_ast = json.dumps(res["ast"])
    assert "ProgramNode" in json_ast

def test_loops_and_arrays():
    code = """
    let nums: int[] = [10, 20, 30];
    foreach (n in nums) {
        if (n == 20) {
            continue;
        }
        print(n);
    }
    let l: int = nums.length();
    """
    res = compile_core(code)
    assert len(res["errors"]) == 0, f"Errors: {res['errors']}"

def test_error_handling():
    code = "let a: int = 10"
    res = compile_core(code)
    assert len(res["errors"]) > 0