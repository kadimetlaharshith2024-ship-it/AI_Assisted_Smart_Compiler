from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ai.assistant import AIAssistant
from app.services.compiler_service import compile_code_full

router = APIRouter()

MAX_CODE_CHARS = 20_000


class CompileRequest(BaseModel):
    code: str = Field(max_length=MAX_CODE_CHARS)


class ExplainRequest(BaseModel):
    code: str = Field(max_length=MAX_CODE_CHARS)
    message: str = Field(min_length=1, max_length=500)
    line: int = 0
    # "simple" is what the "More simplified" button asks for.
    level: Literal["beginner", "simple"] = "simple"
    # The explanation the student found too hard; lets the AI simplify it.
    previous: Optional[str] = Field(default=None, max_length=3_000)


@router.post("/compile")
def compile_source(payload: CompileRequest):
    try:
        result = compile_code_full(payload.code)
        return {
            "status": "success",
            "tokens": result.get("tokens", []),
            "ast": result.get("ast", None),
            "errors": result.get("errors", []),
            "ai_suggestions": result.get("ai_suggestions", []),
            "symbol_table": result.get("symbol_table", None),
            "output": result.get("output", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain")
def explain_error(payload: ExplainRequest):
    """Explain one compiler error at the requested level."""
    try:
        result = AIAssistant().explain(
            payload.code, payload.message, payload.line, payload.level, payload.previous
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "line": payload.line,
        "error": payload.message,
        "level": result["level"],
        "explanation": result["explanation"],
        "source": result["source"],
    }
