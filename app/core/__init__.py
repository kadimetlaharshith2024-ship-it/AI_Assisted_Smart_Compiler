from app.core.lexer import build_lexer
from app.core.parser import parse_code

def compile_core(source_code: str):
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

    return {
        "tokens": token_stream,
        "ast": tree.to_dict() if tree else None,
        "ast_raw": tree,
        "errors": lex_errors + parse_errors
    }