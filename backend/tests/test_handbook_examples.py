"""Every runnable example in the frontend Handbook must compile and run cleanly,
and match its `expectedOutput` when it has one."""
import ast
import re
from pathlib import Path

import pytest

from app.services.compiler_service import compile_code_full

HANDBOOK = Path(__file__).resolve().parents[2] / "frontend" / "src" / "data" / "handbookContent.js"

_EXAMPLE = re.compile(r"code:\s*`(.*?)`(?:\s*,\s*expectedOutput:\s*(\[[^\]]*\]))?", re.DOTALL)
_ESCAPES = {"n": "\n", "t": "\t"}


def load_examples():
    if not HANDBOOK.exists():
        return []
    text = HANDBOOK.read_text(encoding="utf-8")
    examples = []
    for match in _EXAMPLE.finditer(text):
        code = re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), match.group(1))
        expected = ast.literal_eval(match.group(2)) if match.group(2) else None
        examples.append((code, expected))
    return examples


EXAMPLES = load_examples()


def test_handbook_file_was_found():
    if not HANDBOOK.exists():
        pytest.skip("frontend folder not alongside the backend")
    assert len(EXAMPLES) >= 10


@pytest.mark.parametrize("code, expected", EXAMPLES, ids=[f"example-{i}" for i in range(len(EXAMPLES))])
def test_handbook_example_runs_cleanly(code, expected):
    result = compile_code_full(code)
    assert result["errors"] == [], result["errors"]
    assert not any("[Runtime Error" in line for line in result["output"]), result["output"]
    if expected is not None:
        assert result["output"] == expected
