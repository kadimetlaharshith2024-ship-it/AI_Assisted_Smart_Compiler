import pytest
from fastapi.testclient import TestClient

from app.main import app, cors_origins, DEFAULT_CORS_ORIGINS

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_root():
    assert client.get("/").json() == {"message": "Smart Compiler Backend is running!"}

def test_compile_response_shape_for_a_valid_program():
    body = client.post("/api/compile", json={"code": "print(1 + 2);"}).json()
    assert set(body) == {"status", "tokens", "ast", "errors", "ai_suggestions", "symbol_table", "output"}
    assert body["output"] == ["3"] and body["errors"] == [] and body["ai_suggestions"] == []

def test_compile_response_for_a_broken_program():
    body = client.post("/api/compile", json={"code": 'let x: int = "a";'}).json()
    assert body["output"] == [] and len(body["errors"]) == 1
    suggestion = body["ai_suggestions"][0]
    assert suggestion["fix"] is None and suggestion["level"] == "beginner"

def test_runtime_errors_arrive_in_output_with_a_line():
    body = client.post("/api/compile", json={"code": "print(1);\nprint(1 / 0);"}).json()
    assert body["output"] == ["1", "[Runtime Error, line 2] Division by zero"]

def test_oversized_code_is_rejected():
    assert client.post("/api/compile", json={"code": "x" * 20_001}).status_code == 422

def test_missing_code_is_rejected():
    assert client.post("/api/compile", json={}).status_code == 422


# ---- CORS ----

def test_default_cors_origins(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert cors_origins() == DEFAULT_CORS_ORIGINS

def test_cors_origins_from_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " https://a.example.com , https://b.example.com,, ")
    assert cors_origins() == ["https://a.example.com", "https://b.example.com"]

def test_cors_wildcard_is_opt_in(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    assert cors_origins() == ["*"]

def test_empty_cors_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "  ")
    assert cors_origins() == DEFAULT_CORS_ORIGINS

def preflight(origin):
    return client.options("/api/compile", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})

def test_dev_frontend_origin_is_allowed():
    assert preflight("http://localhost:5173").headers.get("access-control-allow-origin") == "http://localhost:5173"

def test_unknown_origin_is_not_allowed():
    assert "access-control-allow-origin" not in preflight("https://evil.example.com").headers
