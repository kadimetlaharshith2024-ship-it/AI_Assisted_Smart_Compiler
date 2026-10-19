"""Pre-demo check: does the real AI work with your key?

Run from the backend folder (venv active):   python check_ai.py
It never prints your key.
"""
import os
import sys

try:                                   # read backend/.env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests

from app.ai.assistant import AIAssistant, clear_cache
from app.services.compiler_service import compile_code_full

BROKEN = 'let age: int = "twenty";\nprint(age);'


def show(text, limit=600):
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + " ..."


def connection_test(assistant):
    """One tiny request, so a bad key / model / quota gives a clear reason."""
    try:
        r = requests.post(
            assistant.api_url,
            headers={"Authorization": f"Bearer {assistant.api_key}", "Content-Type": "application/json"},
            json={"model": assistant.model, "messages": [{"role": "user", "content": "Reply with the single word OK"}],
                  "max_tokens": 5},
            timeout=assistant.timeout,
        )
    except Exception as e:
        print(f"FAIL  Could not reach the AI service: {e}")
        print("      Check your internet connection (or college proxy/firewall).")
        return False
    if r.status_code == 200:
        print(f"PASS  AI service reachable, model '{assistant.model}' answered.")
        return True
    try:
        reason = r.json().get("error", {}).get("message", r.text)
    except Exception:
        reason = r.text
    print(f"FAIL  The AI service answered HTTP {r.status_code}: {show(reason, 300)}")
    hints = {
        401: "The API key is wrong or was copied with extra spaces/quotes. Make a new key and paste it again.",
        403: "This key is not allowed to use that model or region.",
        404: "The model name is wrong. Set LUMEN_AI_MODEL in backend/.env to a model your account can use.",
        429: "No credit left or too many requests. Check billing/usage on the provider's website.",
    }
    if r.status_code in hints:
        print("      " + hints[r.status_code])
    return False


def main():
    if hasattr(sys.stdout, "reconfigure"):          # Windows consoles choke on some characters
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    assistant = AIAssistant()
    if not assistant.api_key:
        print("FAIL  OPENAI_API_KEY is not set.")
        print("      Put  OPENAI_API_KEY=your_key  in backend/.env, save, and run this again.")
        print("      (Without a key the app still works, but with built-in explanations and no fixes.)")
        return 1

    print(f"Model: {assistant.model}\n")
    if not connection_test(assistant):
        return 1

    clear_cache()
    failures = 0

    print("\n--- Test program ---\n" + BROKEN + "\n")
    suggestion = compile_code_full(BROKEN)["ai_suggestions"][0]

    print("1) Beginner explanation")
    if suggestion["source"] == "ai":
        print("PASS  came from the AI:\n" + show(suggestion["explanation"]) + "\n")
    else:
        failures += 1
        print("FAIL  fell back to the built-in tips (the AI call failed).\n")

    print("2) Verified fix")
    fix = suggestion["fix"]
    if fix and fix["verified"]:
        print("PASS  the AI proposed a fix and the compiler verified it. Changes:")
        for c in fix["changes"]:
            for line in c["before"]:
                print(f"      - {line}")
            for line in c["after"]:
                print(f"      + {line}")
        print()
    else:
        failures += 1
        print("FAIL  no verified fix came back. The AI may have replied in an unexpected format;")
        print("      run this again once. If it keeps failing, tell your developer and send this output.\n")

    print("3) 'More simplified' explanation")
    simple = assistant.explain(BROKEN, suggestion["error"], suggestion["line"], "simple", suggestion["explanation"])
    if simple["source"] == "ai":
        print("PASS  came from the AI:\n" + show(simple["explanation"]) + "\n")
    else:
        failures += 1
        print("FAIL  fell back to the built-in tips.\n")

    print("ALL CHECKS PASSED - you're ready to demo." if not failures else f"{failures} check(s) failed - see above.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
