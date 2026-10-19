from concurrent.futures import ThreadPoolExecutor

from app.ai.assistant import AIAssistant
from app.core.interpreter import run_program
from app.core.lexer import build_lexer
from app.services.analysis import analyze
from app.services.fix_verifier import describe_fix, verify_fix

MAX_AI_SUGGESTIONS = 3   # distinct errors explained per compile
MAX_FIX_ATTEMPTS = 2     # first try + one retry using the compiler's feedback


def _suggest(assistant, source_code, error, all_errors):
    """Explain one error and, when the AI proposes a fix, verify it by compiling it.

    A fix is only attached when it passes verification; a rejected fix is
    retried once with the compiler's feedback and otherwise dropped, so the
    student never sees a wrong fix presented as correct."""
    message, line = error["message"], error.get("line", 0)
    result = assistant.explain_with_fix(source_code, message, line)
    explanation, source = result["explanation"], result["source"]

    fix = None
    attempt, rejected, reason, remaining = 1, None, None, None
    while result["fixed_code"]:
        verdict = verify_fix(source_code, all_errors, message, result["fixed_code"])
        if verdict.verified:
            fix = describe_fix(source_code, result["fixed_code"], verdict)
            explanation = result["explanation"]
            break
        if attempt >= MAX_FIX_ATTEMPTS:
            break
        attempt += 1
        rejected, reason, remaining = result["fixed_code"], verdict.reason, verdict.remaining_errors
        result = assistant.explain_with_fix(source_code, message, line, rejected, reason, remaining)

    return {
        "line": line,
        "error": message,
        "explanation": explanation,
        "level": "beginner",
        "source": source,
        "fix": fix,
    }


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

    analysis = analyze(source_code)
    tree, all_errors = analysis.tree, analysis.errors

    # Explain each *distinct* error message. Capped, and run in parallel so a
    # program with several errors costs one round-trip of latency, not several.
    distinct, seen_messages = [], set()
    for err in all_errors:
        if len(distinct) >= MAX_AI_SUGGESTIONS:
            break
        if err["message"] in seen_messages:
            continue
        seen_messages.add(err["message"])
        distinct.append(err)

    ai_suggestions = []
    if distinct:
        assistant = AIAssistant()
        with ThreadPoolExecutor(max_workers=len(distinct)) as pool:
            ai_suggestions = list(pool.map(
                lambda e: _suggest(assistant, source_code, e, all_errors), distinct))

    symbol_table = analysis.checker.global_scope.to_dict() if analysis.checker else None

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
