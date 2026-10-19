"""Checks an AI-proposed fix by running it through the real compiler front end."""
from collections import Counter
from dataclasses import dataclass, field
from typing import List

from app.ai.fixes import fix_changes, normalize_message, MAX_FIXED_CODE_CHARS
from app.services.analysis import analyze


@dataclass
class FixVerdict:
    verified: bool
    resolves_all: bool = False                       # fixed program has no errors at all
    reason: str = ""
    remaining_errors: List[str] = field(default_factory=list)


def verify_fix(original_code, original_errors, target_message, fixed_code):
    """A fix is verified when, after compiling the fixed program:
      1. the targeted error is gone, and
      2. it introduced no error that the original program didn't already have.
    Other pre-existing errors may remain: each error gets its own fix, and a
    fix for one must not be rejected because the student has other mistakes."""
    if not fixed_code or fixed_code.strip() == original_code.strip():
        return FixVerdict(False, reason="the fix doesn't change the program")
    if len(fixed_code) > MAX_FIXED_CODE_CHARS:
        return FixVerdict(False, reason="the fix is too large")

    target = normalize_message(target_message)
    original = Counter(normalize_message(e["message"]) for e in original_errors)
    fixed_errors = [normalize_message(e["message"]) for e in analyze(fixed_code).errors]

    if target in fixed_errors:
        return FixVerdict(False, reason="the error is still there", remaining_errors=fixed_errors)
    new_errors = [m for m in fixed_errors if m not in original]
    if new_errors:
        return FixVerdict(False, reason="the fix introduced new errors", remaining_errors=new_errors)
    return FixVerdict(True, resolves_all=not fixed_errors, remaining_errors=fixed_errors)


def describe_fix(original_code, fixed_code, verdict):
    return {
        "code": fixed_code,
        "verified": True,
        "resolves_all": verdict.resolves_all,
        "changes": fix_changes(original_code, fixed_code),
    }
