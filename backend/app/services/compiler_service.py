from app.core.lexer import build_lexer
from app.core.parser import parse_code
from app.core.interpreter import run_program
from app.semantic.type_checker import TypeChecker
from app.ai.assistant import AIAssistant

def compile_code_full(source_code: str):
    lexer = build_lexer()
    lexer.input(source_code)
    token_stream = []
    for tok in lexer:
        token_stream.append({
            "type": tok.type,
            "value": str(tok.value),
            "line": tok.lineno,
            "lexpos": tok.lexpos
        })

    tree, lex_errors, parse_errors = parse_code(source_code)
    
    semantic_errors = []
    ai_suggestions = []

    if tree and not (lex_errors or parse_errors):
        checker = TypeChecker()
        try:
            semantic_errors = checker.visit(tree)
        except Exception as e:
            semantic_errors = [{"line": 0, "message": str(e)}]

    all_errors = lex_errors + parse_errors + semantic_errors
    assistant = AIAssistant()

    # Explain each *distinct* error message (cap to avoid hammering the AI
    # service / slowing the response down when a program has many errors).
    MAX_AI_SUGGESTIONS = 3
    seen_messages = set()
    for err in all_errors:
        if len(ai_suggestions) >= MAX_AI_SUGGESTIONS:
            break
        message = err["message"]
        if message in seen_messages:
            continue
        seen_messages.add(message)
        explanation = assistant.explain_error(source_code, message)
        ai_suggestions.append({
            "line": err.get("line", 0),
            "error": message,
            "explanation": explanation
        })

    symbol_table = checker.global_scope.to_dict() if (tree and not (lex_errors or parse_errors)) else None

    output = []
    if tree and not all_errors:
        try:
            output = run_program(tree)
        except Exception as e:
            output = [f"[Runtime Error] {e}"]

    return {
        "tokens": token_stream,
        "ast": tree.to_dict() if tree else None,
        "ast_raw": tree,
        "errors": all_errors,
        "ai_suggestions": ai_suggestions,
        "symbol_table": symbol_table,
        "output": output
    }

class CompilerService:
    @staticmethod
    def compile(source_code: str):
        return compile_code_full(source_code)