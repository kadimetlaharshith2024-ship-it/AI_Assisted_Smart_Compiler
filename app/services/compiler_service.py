from app.core import compile_core

class CompilerService:
    @staticmethod
    def process_source(source_code: str) -> dict:
        result = compile_core(source_code)
        return {
            "success": len(result["errors"]) == 0,
            "tokens": result["tokens"],
            "ast": result["ast"],
            "ast_raw": result["ast_raw"],  # Direct Python objects for Saran's analyzer
            "errors": result["errors"]
        }