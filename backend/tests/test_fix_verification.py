import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.ai import assistant as assistant_module
from app.ai.assistant import clear_cache
from app.ai.fixes import fix_changes, normalize_message, parse_model_json
from app.services.analysis import analyze
from app.services.compiler_service import compile_code_full
from app.services.fix_verifier import verify_fix

BROKEN = 'let age: int = "twenty";\nprint(age);'
FIXED = 'let age: int = 20;\nprint(age);'
ERR = "Cannot initialize 'age' of type 'int' with a value of type 'string'"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LUMEN_AI_API_URL", raising=False)
    clear_cache()
    yield
    clear_cache()


class FakeResponse:
    status_code = 200

    def __init__(self, text):
        self._text = text

    def json(self):
        return {"choices": [{"message": {"content": self._text}}]}


@pytest.fixture
def ai(monkeypatch):
    """Turn the AI on. Set `ai.responder = lambda user_prompt: str` to script replies."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class Fake:
        calls = []
        responder = staticmethod(lambda user: json.dumps({"explanation": "because", "fixed_code": None}))

    def fake_post(url, json=None, headers=None, timeout=None):
        Fake.calls.append(json)
        return FakeResponse(Fake.responder(json["messages"][1]["content"]))

    Fake.calls = []
    monkeypatch.setattr(assistant_module.requests, "post", fake_post)
    return Fake


def reply(explanation="Because.", fixed_code=None):
    return json.dumps({"explanation": explanation, "fixed_code": fixed_code})


# ---- parse_model_json ----

def test_parse_plain_json():
    assert parse_model_json(reply("hi", "x")) == ("hi", "x")

def test_parse_json_in_code_fence():
    assert parse_model_json("```json\n" + reply("hi", "x") + "\n```") == ("hi", "x")

def test_parse_json_with_surrounding_prose():
    assert parse_model_json("Sure! " + reply("hi", "x") + " Hope that helps.") == ("hi", "x")

def test_parse_non_json_becomes_explanation_without_fix():
    assert parse_model_json("just words") == ("just words", None)

@pytest.mark.parametrize("fixed", [None, "", "   ", 5, ["a"]])
def test_parse_rejects_unusable_fixed_code(fixed):
    assert parse_model_json(json.dumps({"explanation": "e", "fixed_code": fixed})) == ("e", None)

def test_parse_rejects_huge_fixed_code():
    assert parse_model_json(reply("e", "x" * 20_001)) == ("e", None)

def test_parse_empty():
    assert parse_model_json("") == (None, None) and parse_model_json(None) == (None, None)

def test_normalize_message_drops_lexer_line_suffix():
    assert normalize_message("Illegal character '@' at line 7") == "Illegal character '@'"
    assert normalize_message(ERR) == ERR


# ---- fix_changes ----

def test_changes_replace_one_line():
    assert fix_changes(BROKEN, FIXED) == [
        {"line": 1, "before": ['let age: int = "twenty";'], "after": ["let age: int = 20;"]}]

def test_changes_insert_and_delete():
    assert fix_changes("a\nc", "a\nb\nc") == [{"line": 2, "before": [], "after": ["b"]}]
    assert fix_changes("a\nb\nc", "a\nc") == [{"line": 2, "before": ["b"], "after": []}]

def test_changes_identical():
    assert fix_changes("a\nb", "a\nb") == []


# ---- verify_fix ----

def errors_of(code):
    return analyze(code).errors

def test_good_fix_is_verified_and_resolves_everything():
    verdict = verify_fix(BROKEN, errors_of(BROKEN), ERR, FIXED)
    assert verdict.verified and verdict.resolves_all

def test_unchanged_program_is_rejected():
    assert not verify_fix(BROKEN, errors_of(BROKEN), ERR, BROKEN).verified
    assert not verify_fix(BROKEN, errors_of(BROKEN), ERR, "").verified

def test_fix_that_leaves_the_error_is_rejected():
    verdict = verify_fix(BROKEN, errors_of(BROKEN), ERR, 'let age: int = "thirty";\nprint(age);')
    assert not verdict.verified and "still there" in verdict.reason

def test_fix_that_introduces_a_new_error_is_rejected():
    verdict = verify_fix(BROKEN, errors_of(BROKEN), ERR, 'let age: int = 20.5;\nprint(age);')
    # a float literal is still an int/float mismatch: a *different* message from the target
    assert not verdict.verified

def test_fix_with_syntax_error_is_rejected():
    verdict = verify_fix(BROKEN, errors_of(BROKEN), ERR, 'let age: int = 20\nprint(age);')
    assert not verdict.verified and verdict.remaining_errors

def test_other_existing_errors_may_remain():
    code = 'let a: int = "x";\nlet b: bool = 3;'
    errs = errors_of(code)
    verdict = verify_fix(code, errs, errs[0]["message"], 'let a: int = 1;\nlet b: bool = 3;')
    assert verdict.verified and not verdict.resolves_all and len(verdict.remaining_errors) == 1


# ---- the full loop through compile_code_full ----

def test_verified_fix_is_attached(ai):
    ai.responder = lambda user: reply("The box holds numbers.", FIXED)
    suggestion = compile_code_full(BROKEN)["ai_suggestions"][0]
    assert suggestion["explanation"] == "The box holds numbers."
    assert suggestion["source"] == "ai" and suggestion["level"] == "beginner"
    fix = suggestion["fix"]
    assert fix["verified"] and fix["resolves_all"] and fix["code"] == FIXED
    assert fix["changes"][0]["after"] == ["let age: int = 20;"]
    assert len(ai.calls) == 1

def test_rejected_fix_is_retried_with_compiler_feedback(ai):
    replies = iter([reply("first", 'let age: int = "thirty";\nprint(age);'), reply("second", FIXED)])
    prompts = []

    def responder(user):
        prompts.append(user)
        return next(replies)

    ai.responder = responder
    suggestion = compile_code_full(BROKEN)["ai_suggestions"][0]
    assert suggestion["fix"]["code"] == FIXED
    assert suggestion["explanation"] == "second"        # explanation matches the fix that was kept
    assert len(prompts) == 2
    assert "rejected by the compiler" in prompts[1] and "the error is still there" in prompts[1]
    assert "thirty" in prompts[1]

def test_fix_rejected_twice_is_dropped_but_explanation_kept(ai):
    bad = 'let age: int = "thirty";\nprint(age);'
    ai.responder = lambda user: reply("why it failed", bad)
    suggestion = compile_code_full(BROKEN)["ai_suggestions"][0]
    assert suggestion["fix"] is None and suggestion["explanation"] == "why it failed"
    assert len(ai.calls) == 2                            # one retry, no more

def test_reply_without_json_gives_explanation_only(ai):
    ai.responder = lambda user: "Plain text answer"
    suggestion = compile_code_full(BROKEN)["ai_suggestions"][0]
    assert suggestion["explanation"] == "Plain text answer" and suggestion["fix"] is None
    assert len(ai.calls) == 1

def test_null_fixed_code_means_no_fix(ai):
    ai.responder = lambda user: reply("no safe fix", None)
    assert compile_code_full(BROKEN)["ai_suggestions"][0]["fix"] is None

def test_offline_mode_never_proposes_fixes():
    suggestion = compile_code_full(BROKEN)["ai_suggestions"][0]
    assert suggestion["source"] == "offline" and suggestion["fix"] is None

def test_large_programs_skip_the_fix_request(ai):
    big = BROKEN + "\n" + "\n".join(f"print({i});" for i in range(2000))
    ai.responder = lambda user: "markdown explanation"
    suggestion = compile_code_full(big)["ai_suggestions"][0]
    assert suggestion["fix"] is None
    assert "response_format" not in ai.calls[0]
    assert "JSON" not in ai.calls[0]["messages"][0]["content"]

def test_json_mode_only_requested_for_openai(ai, monkeypatch):
    compile_code_full(BROKEN)
    assert ai.calls[0]["response_format"] == {"type": "json_object"}
    ai.calls.clear(); clear_cache()
    monkeypatch.setenv("LUMEN_AI_API_URL", "http://localhost:9999/v1/chat/completions")
    compile_code_full(BROKEN)
    assert "response_format" not in ai.calls[0]

def test_each_error_gets_its_own_verified_fix_in_parallel(ai):
    code = 'let a: int = "x";\nlet b: bool = 3;\nlet c: int = zzz;'
    fixes = {
        "Cannot initialize 'a'": 'let a: int = 1;\nlet b: bool = 3;\nlet c: int = zzz;',
        "Cannot initialize 'b'": 'let a: int = "x";\nlet b: bool = true;\nlet c: int = zzz;',
        "Undeclared identifier 'zzz'": 'let a: int = "x";\nlet b: bool = 3;\nlet c: int = 0;',
    }

    def responder(user):
        for marker, fixed in fixes.items():
            if f"Compiler error to fix: {marker}" in user:
                return reply(f"fix for {marker}", fixed)
        raise AssertionError(user)

    ai.responder = responder
    suggestions = compile_code_full(code)["ai_suggestions"]
    assert [s["line"] for s in suggestions] == [1, 2, 3]
    for s in suggestions:
        assert s["fix"] and s["fix"]["verified"] and not s["fix"]["resolves_all"]


# ---- the parser must be safe to use from many threads ----

def test_analyze_is_thread_safe():
    """Regression test for a shared-parser race. It forces very frequent thread
    switches, because with the default switch interval the race almost never
    shows up in a short run."""
    import sys

    programs = [
        ("let a: int = 1;", 0),
        ('let a: int = "x";', 1),
        ("let a: int = 1", 1),                 # syntax error
        ("let a: int = 1; let b: int = a;", 0),
        ("let a: int = zzz; let b: int = yyy;", 2),
    ]
    jobs = programs * 600

    def count_errors(job):
        try:
            return len(analyze(job[0]).errors)
        except Exception as e:                  # a corrupted parse can also raise
            return repr(e)

    previous = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(count_errors, jobs))
    finally:
        sys.setswitchinterval(previous)
    assert results == [expected for _, expected in jobs]
