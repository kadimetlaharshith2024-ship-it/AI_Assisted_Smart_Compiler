"""Helpers for AI-proposed fixes: parsing the model's JSON reply, comparing
programs, and describing what a fix changes."""
import difflib
import json
import re

MAX_FIX_SOURCE_CHARS = 6_000     # the model must echo the whole program, so keep it small
MAX_FIXED_CODE_CHARS = 20_000

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_model_json(text):
    """Return (explanation, fixed_code) from the model's reply.

    The model is asked for {"explanation": ..., "fixed_code": ...}. Replies are
    parsed leniently (code fences, extra prose). If no JSON object can be found,
    the whole reply is treated as the explanation and there is no fix."""
    if not text:
        return None, None
    cleaned = _FENCE.sub("", text.strip()).strip()
    candidates = [cleaned]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        candidates.append(cleaned[start:end + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("explanation"), str):
            fixed = data.get("fixed_code")
            if not isinstance(fixed, str) or not fixed.strip() or len(fixed) > MAX_FIXED_CODE_CHARS:
                fixed = None
            return data["explanation"].strip(), fixed
    return text.strip(), None


def normalize_message(message):
    """Error text without the line suffix the lexer adds, so the same problem
    on a different line still counts as the same error."""
    return re.sub(r"\s+at line \d+", "", message).strip()


def fix_changes(original, fixed):
    """Describe a fix as a list of changes against the original program:
    {"line": first affected original line, "before": [...], "after": [...]}"""
    old_lines, new_lines = original.splitlines(), fixed.splitlines()
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    changes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changes.append({
            "line": min(i1 + 1, max(len(old_lines), 1)),
            "before": old_lines[i1:i2],
            "after": new_lines[j1:j2],
        })
    return changes
