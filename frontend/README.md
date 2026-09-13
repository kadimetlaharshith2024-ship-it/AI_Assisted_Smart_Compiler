# Lumen Frontend

React + CodeMirror frontend for the Lumen compiler: a **Handbook** (learn the
language) and a **Playground** (write and run code against the real
FastAPI backend).

## Setup

```bash
npm install
cp .env.example .env   # adjust VITE_API_URL if your backend isn't on :8000
npm run dev
```

Runs at http://localhost:5173. Make sure the backend is running (with the
CORS fix applied — see the backend repo) at the URL in `.env`.

## Structure

```
src/
  App.jsx                 top bar + Handbook/Playground mode switch
  api.js                  fetch wrapper for POST /api/compile
  data/handbookContent.js all lesson content (edit this to update the Handbook)
  pages/
    HandbookPage.jsx       lesson rail + content, "Run in Playground" buttons
    Playground.jsx         editor + run button + status strip + output panel
  components/
    CodeEditor.jsx          CodeMirror wrapper with error-line highlighting
    OutputPanel.jsx         Output / Tokens / AST / Symbol Table / Errors & AI tabs
    AstTree.jsx             recursive renderer for the ast JSON tree
  styles/global.css         design tokens + all component styles
```

## Editing the Handbook

Add or edit lessons in `src/data/handbookContent.js`. Each lesson supports:

- `intro` — prose paragraph
- `typeTable` — optional table (used for the Variables & Types lesson)
- `examples` — array of `{ label, code }`, each rendered with a
  "Run in Playground" button
- `subsections` — for lessons with multiple parts (e.g. Loops: while/for/foreach)
- `keywords` — optional chip list (used for the Reserved Keywords lesson)

Every example currently in the Handbook has been run against the real
backend to confirm it compiles and executes without errors — if you add new
examples, test them against `/api/compile` before shipping, since a broken
"Try it" button is worse than not having one.

## Known scope limits (by design, for now)

- The Symbol Table tab only shows **global scope** — function parameters and
  loop-local variables aren't kept after type-checking finishes on the
  backend. Fine for teaching top-level declarations; not a full scope
  inspector.
- CodeMirror is set up with the JavaScript grammar for syntax highlighting
  since Lumen's C-family syntax is close enough — keywords like `let`/`fn`/
  `foreach` won't be specially colored, but braces/strings/numbers/comments
  will look right.
