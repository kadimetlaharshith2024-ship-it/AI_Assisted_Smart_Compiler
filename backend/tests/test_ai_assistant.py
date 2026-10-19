import re

import pytest
from fastapi.testclient import TestClient

from app.ai import assistant as assistant_module
from app.ai.assistant import AIAssistant, build_excerpt, clear_cache
from app.ai.offline import explain_offline
from app.main import app
from app.services.compiler_service import compile_code_full


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Every test starts offline with an empty cache; tests opt in to a key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    clear_cache()
    yield
    clear_cache()


class FakeResponse:
    def __init__(self, text="AI says hi", status=200):
        self.status_code = status
        self._text = text

    def json(self):
        return {"choices": [{"message": {"content": self._text}}]}


@pytest.fixture
def fake_ai(monkeypatch):
    """Turn the AI on and record every request instead of calling OpenAI."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse(f"reply #{len(calls)}")

    monkeypatch.setattr(assistant_module.requests, "post", fake_post)
    return calls


# ---- excerpt ----

def test_excerpt_marks_error_line_and_limits_context():
    source = "\n".join(f"line{i}" for i in range(1, 101))
    excerpt = build_excerpt(source, 50)
    assert "> 50 | line50" in excerpt
    assert "line47" in excerpt and "line53" in excerpt
    assert "line46" not in excerpt and "line54" not in excerpt

def test_excerpt_without_usable_line_is_capped():
    source = "\n".join(f"line{i}" for i in range(1, 200))
    assert build_excerpt(source, -1).count("\n") + 1 == 40


# ---- offline mode: both levels work and differ ----

def test_offline_levels_differ_and_mention_the_name():
    beginner = explain_offline("Undeclared identifier 'score'", "beginner")
    simple = explain_offline("Undeclared identifier 'score'", "simple")
    assert beginner != simple
    assert "score" in beginner and "score" in simple
    assert simple.startswith("**In plain words:**")

@pytest.mark.parametrize("message", [
    "Undeclared identifier 'x'", "Undeclared function 'go'",
    "Cannot initialize 'x' of type 'int' with a value of type 'string'",
    "Cannot assign a value of type 'string' to variable 'x' of type 'int'",
    "Cannot assign a value of type 'string' to an array element of type 'int'",
    "Function 'f' must return 'int', but this returns 'string'",
    "Function 'f' is declared 'void' and cannot return a value",
    "Function 'f' must return a value of type 'int' on every path",
    "Function 'f' must return a value of type 'int'",
    "Argument 1 of 'f' expects 'int', got 'string'",
    "Function 'f' expects 1 arguments, but 2 were provided",
    "'if' condition must be of type 'bool', got 'int'",
    "Cannot concatenate 'string' and 'int': '+' joins two strings only",
    "Operator '-' cannot be applied to 'string' and 'int'",
    "Variable 'x' is already declared in this scope",
    "'break' can only be used inside a loop",
    "Syntax error at ';'", "Unexpected end of input", "Illegal character '@' at line 1",
    "Something the rules have never seen",
])
def test_offline_covers_every_message_family_at_both_levels(message):
    for level in ("beginner", "simple"):
        text = explain_offline(message, level)
        assert text.strip()
        assert not re.search(r"\{[a-z_0-9]+\}", text), text   # no unfilled {placeholders}
        assert "{{" not in text and "}}" not in text           # no leaked brace escapes

def test_offline_type_mismatch_names_both_types():
    text = explain_offline("Cannot initialize 'x' of type 'int' with a value of type 'string'", "simple")
    assert "`int`" in text and "`string`" in text


# ---- AIAssistant.explain ----

def test_offline_result_is_flagged():
    result = AIAssistant().explain("let x: int = y;", "Undeclared identifier 'y'", 1, "simple")
    assert result["source"] == "offline" and result["level"] == "simple" and result["explanation"]

def test_invalid_level_rejected():
    with pytest.raises(ValueError):
        AIAssistant().explain("x", "m", 1, "expert")

def test_levels_use_different_prompts(fake_ai):
    assistant = AIAssistant()
    assistant.explain("let x: int = y;", "Undeclared identifier 'y'", 1, "beginner")
    assistant.explain("let x: int = y;", "Undeclared identifier 'y'", 1, "simple")
    beginner_system = fake_ai[0]["json"]["messages"][0]["content"]
    simple_system = fake_ai[1]["json"]["messages"][0]["content"]
    assert "15-year-old" in simple_system and "15-year-old" not in beginner_system
    assert "beginner-friendly" in beginner_system

def test_user_prompt_contains_error_line_and_numbered_code(fake_ai):
    AIAssistant().explain("let a: int = 1;\nlet x: int = y;\nprint(x);", "Undeclared identifier 'y'", 2, "beginner")
    user = fake_ai[0]["json"]["messages"][1]["content"]
    assert "Undeclared identifier 'y'" in user and "line: 2" in user
    assert "> 2 | let x: int = y;" in user

def test_simple_prompt_includes_previous_explanation(fake_ai):
    AIAssistant().explain("x", "m", 1, "simple", previous="too hard text")
    assert "too hard text" in fake_ai[0]["json"]["messages"][1]["content"]

def test_beginner_prompt_ignores_previous_explanation(fake_ai):
    AIAssistant().explain("x", "m", 1, "beginner", previous="too hard text")
    assert "too hard text" not in fake_ai[0]["json"]["messages"][1]["content"]

def test_model_and_url_are_configurable(fake_ai, monkeypatch):
    monkeypatch.setenv("LUMEN_AI_MODEL", "my-model")
    monkeypatch.setenv("LUMEN_AI_API_URL", "http://localhost:1234/v1/chat/completions")
    AIAssistant().explain("x", "m", 1)
    assert fake_ai[0]["json"]["model"] == "my-model"
    assert fake_ai[0]["url"] == "http://localhost:1234/v1/chat/completions"
    assert fake_ai[0]["headers"]["Authorization"] == "Bearer test-key"

def test_successful_ai_answers_are_cached(fake_ai):
    assistant = AIAssistant()
    first = assistant.explain("x", "m", 1, "simple")
    second = assistant.explain("x", "m", 1, "simple")
    assert len(fake_ai) == 1 and first == second and first["source"] == "ai"

def test_levels_are_cached_separately(fake_ai):
    assistant = AIAssistant()
    assistant.explain("x", "m", 1, "beginner")
    assistant.explain("x", "m", 1, "simple")
    assert len(fake_ai) == 2

def test_ai_failure_falls_back_to_offline_and_is_not_cached(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    calls = []

    def boom(*a, **kw):
        calls.append(1)
        raise ConnectionError("no network")

    monkeypatch.setattr(assistant_module.requests, "post", boom)
    assistant = AIAssistant()
    result = assistant.explain("x", "Undeclared identifier 'y'", 1, "simple")
    assert result["source"] == "offline" and "y" in result["explanation"]
    assistant.explain("x", "Undeclared identifier 'y'", 1, "simple")
    assert len(calls) == 2   # failures aren't cached

def test_bad_status_falls_back_to_offline(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setattr(assistant_module.requests, "post", lambda *a, **kw: FakeResponse(status=429))
    assert AIAssistant().explain("x", "Undeclared identifier 'y'", 1)["source"] == "offline"


# ---- compile contract ----

def test_compile_returns_beginner_suggestions_with_metadata():
    result = compile_code_full("let x: int = y + 10;")
    suggestion = result["ai_suggestions"][0]
    assert suggestion["level"] == "beginner" and suggestion["source"] == "offline"
    assert suggestion["error"] == "Undeclared identifier 'y'" and suggestion["line"] == 1

def test_compile_explains_distinct_errors_in_order_and_caps_at_three(fake_ai):
    code = 'let a: int = "1";\nlet b: int = "2";\nlet c: bool = 3;\nlet d: int = q;\nlet e: int = r;'
    result = compile_code_full(code)
    assert len(result["ai_suggestions"]) == 3
    assert [s["line"] for s in result["ai_suggestions"]] == [1, 2, 3]
    assert len(fake_ai) == 3

def test_compile_without_errors_makes_no_ai_calls(fake_ai):
    result = compile_code_full("print(1);")
    assert result["ai_suggestions"] == [] and fake_ai == []


# ---- /api/explain ----

client = TestClient(app)

def test_explain_endpoint_defaults_to_simple():
    r = client.post("/api/explain", json={"code": "let x: int = y;", "message": "Undeclared identifier 'y'", "line": 1})
    body = r.json()
    assert r.status_code == 200
    assert body["level"] == "simple" and body["source"] == "offline"
    assert body["explanation"].startswith("**In plain words:**")

def test_explain_endpoint_beginner_level():
    r = client.post("/api/explain", json={"code": "x", "message": "Undeclared identifier 'y'", "line": 1, "level": "beginner"})
    assert r.json()["explanation"].startswith("**What went wrong:**")

def test_explain_endpoint_passes_previous_to_ai(fake_ai):
    r = client.post("/api/explain", json={"code": "x", "message": "m", "line": 1, "level": "simple", "previous": "old text"})
    assert r.status_code == 200 and r.json()["source"] == "ai"
    assert "old text" in fake_ai[0]["json"]["messages"][1]["content"]

@pytest.mark.parametrize("payload", [
    {"code": "x", "message": "m", "level": "expert"},
    {"code": "x", "message": ""},
    {"code": "x" * 20_001, "message": "m"},
    {"message": "m"},
])
def test_explain_endpoint_validates_input(payload):
    assert client.post("/api/explain", json=payload).status_code == 422
