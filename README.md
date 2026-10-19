# Lumen — AI-Assisted Smart Compiler

Lumen is a small C-style teaching language with a web playground. You write code
in the browser, and the backend lexes, parses, type-checks and runs it. When your
code has errors, an AI assistant explains each one in beginner-friendly language,
can explain it again "more simplified" (as if to a 15-year-old who just started
coding), and may propose a fix that has been **verified by compiling it**.

```
frontend/   React + Vite + CodeMirror: Handbook (learn Lumen) and Playground
backend/    FastAPI + PLY: lexer, parser, type checker, interpreter, AI assistant
```

## How it works

```
source ─► lexer ─► parser ─► AST ─► type checker ─► interpreter ─► output
          (PLY)    (PLY)           (symbol table)   (tree-walking)
                                        │
                                  errors ──► AI assistant ─► explanation (+ verified fix)
```

| Stage | Where | What it does |
|---|---|---|
| Lexer / parser | `app/core/lexer.py`, `parser.py` | PLY tokens and grammar → AST (`app/core/ast/`) |
| Type checker | `app/semantic/type_checker.py` | Declarations, scopes, assignment/return/argument types, bool conditions, array types, `break`/`return` placement, "returns on every path" |
| Interpreter | `app/core/interpreter.py` | Runs the AST; step, time, call-depth and output limits protect the server |
| AI assistant | `app/ai/` | Prompts, offline explanations, caching, fix proposals |
| Fix verifier | `app/services/fix_verifier.py` | Compiles an AI-proposed fix before it is shown |

### Is it a compiler or an interpreter?

Both halves of the name are fair, with one caveat. The **front end** (lexing,
parsing, semantic analysis with a symbol table and type checking, rich error
reporting) is what a compiler does. The **back end** does not generate machine
code or bytecode: it executes the checked AST directly with a tree-walking
interpreter. So Lumen is best described as *a compiler front end plus an
interpreter*. That is a common design for teaching languages, and it is why the
playground can show tokens, the AST and the symbol table.

## The AI assistant

- **Beginner-friendly explanation** for every error (up to 3 distinct errors per run).
- **✨ More simplified** button: re-explains the same error for a 15-year-old who
  just started coding (short sentences, one everyday analogy, no jargon).
- **Verified fixes:** with an AI key, the assistant proposes a complete fixed
  program. The backend compiles it; the fix is shown only if the targeted error is
  gone and no new error appeared. A rejected fix is retried once, using the
  compiler's feedback, then dropped. Verified fixes have an **Apply fix** button.
  "Verified" means *it compiles under Lumen's rules*, not that it does what you meant.
- **No key? Still works.** Built-in explanations cover every compiler message at
  both levels (tagged "Built-in tips"); fixes are only offered when an AI is available.

## Run it

Backend (developed and tested on Python 3.12):

```bash
cd backend
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                  # optional: add OPENAI_API_KEY
uvicorn app.main:app --reload --env-file .env
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env     # VITE_API_URL, defaults to http://localhost:8000
npm run dev              # http://localhost:5173
```

Tests: `cd backend && pytest`

### Backend settings (environment variables, all optional)

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | *(none)* | Enables AI explanations and fix proposals |
| `LUMEN_AI_MODEL` | `gpt-4o-mini` | Chat model name |
| `LUMEN_AI_API_URL` | OpenAI chat-completions URL | Any OpenAI-compatible endpoint |
| `LUMEN_AI_TIMEOUT` | `12` | Seconds to wait for the AI |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed frontend origin(s), comma-separated |

## API

| Endpoint | Body | Returns |
|---|---|---|
| `POST /api/compile` | `{ "code": "..." }` (max 20,000 chars) | `tokens`, `ast`, `errors`, `ai_suggestions`, `symbol_table`, `output` |
| `POST /api/explain` | `{ "code", "message", "line", "level": "beginner" \| "simple", "previous"? }` | `{ line, error, level, explanation, source }` |

Each item in `ai_suggestions` is
`{ line, error, explanation, level, source: "ai" \| "offline", fix }`, where `fix`
is `null` or `{ code, verified, resolves_all, changes: [{ line, before, after }] }`.

## Runtime limits

A run stops with a clear `[Runtime Error]` after 1,000,000 steps, 3 seconds, 200
nested calls or 5,000 output lines (constants at the top of `interpreter.py`).

## Known limits

- The Symbol Table tab shows global-scope declarations only.
- Functions must be declared at the top level; there are no closures.
- `int` converts to `float` implicitly; there are no other implicit conversions.
- Arrays are references, so assigning one array variable to another shares it.
