"""Front-end analysis shared by the compile pipeline and the fix verifier:
lex + parse + semantic check, with no AI calls and no execution."""
from dataclasses import dataclass, field
from typing import Any, List, Optional

from app.core.parser import parse_code
from app.semantic.type_checker import TypeChecker


@dataclass
class Analysis:
    tree: Any = None
    errors: List[dict] = field(default_factory=list)
    checker: Optional[TypeChecker] = None   # only set when the type checker ran
    syntax_ok: bool = False                  # no lex/parse errors


def analyze(source_code: str) -> Analysis:
    tree, lex_errors, parse_errors = parse_code(source_code)
    syntax_ok = bool(tree) and not (lex_errors or parse_errors)

    semantic_errors, checker = [], None
    if syntax_ok:
        checker = TypeChecker()
        try:
            semantic_errors = checker.visit(tree)
        except Exception as e:
            semantic_errors = [{"line": 0, "message": str(e)}]

    return Analysis(
        tree=tree,
        errors=lex_errors + parse_errors + semantic_errors,
        checker=checker,
        syntax_ok=syntax_ok,
    )
