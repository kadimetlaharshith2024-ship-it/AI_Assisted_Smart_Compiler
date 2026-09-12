from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.compiler_service import compile_code_full

router = APIRouter()

class CompileRequest(BaseModel):
    code: str

@router.post("/compile")
def compile_source(payload: CompileRequest):
    try:
        result = compile_code_full(payload.code)
        return {
            "status": "success",
            "tokens": result.get("tokens", []),
            "ast": result.get("ast", None),
            "errors": result.get("errors", []),
            "ai_suggestions": result.get("ai_suggestions", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))