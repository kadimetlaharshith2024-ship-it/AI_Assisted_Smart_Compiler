import pytest
from app.services.compiler_service import compile_code_full

def test_valid_factorial_semantics():
    code = """
    fn factorial(n: int) -> int {
        if (n <= 1) {
            return 1;
        }
        return n * factorial(n - 1);
    }
    fn main() -> void {
        let limit: int = 6;
        let f: int = factorial(limit);
        print(f);
    }
    main();
    """
    result = compile_code_full(code)
    assert len(result["errors"]) == 0, f"Expected no errors, got {result['errors']}"
    assert result["ast"] is not None

def test_semantic_undeclared_variable():
    code = """
    let x: int = y + 10;
    """
    result = compile_code_full(code)
    assert len(result["errors"]) > 0
    # Verify AI assistant catches the semantic error and provides suggestions
    assert len(result["ai_suggestions"]) > 0
    print("AI Suggestion received:", result["ai_suggestions"][0])


def test_ai_error_explanation():
    code = """
    let x: int = y + 10;
    """
    result = compile_code_full(code)
    
    print("\n--- AI SUGGESTION OUTPUT ---")
    for suggestion in result["ai_suggestions"]:
        print(suggestion)
    print("----------------------------\n")
    
    assert len(result["ai_suggestions"]) > 0    