from app.core.lexer import build_lexer
from app.core.parser import parse_code
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
    
    if all_errors:
        primary_error = all_errors[0]["message"]
        ai_suggestion = assistant.explain_error(source_code, primary_error)
        ai_suggestions.append(ai_suggestion)

    return {
        "tokens": token_stream,
        "ast": tree.to_dict() if tree else None,
        "ast_raw": tree,
        "errors": all_errors,
        "ai_suggestions": ai_suggestions
    }

class CompilerService:
    @staticmethod
    def compile(source_code: str):
        return compile_code_full(source_code)