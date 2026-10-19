const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Sends source code to the backend and returns the parsed compile result.
 * Matches the real /api/compile contract:
 * { status, tokens, ast, errors, ai_suggestions, symbol_table, output }
 */
export async function compileCode(code) {
  const res = await fetch(`${API_URL}/api/compile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  })

  if (!res.ok) {
    // FastAPI's HTTPException(500, detail=...) shape
    let detail = `Request failed with status ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // response wasn't JSON — keep the generic message
    }
    throw new Error(detail)
  }

  return res.json()
}

/**
 * Asks the backend to explain one compiler error at a given level.
 * level: 'beginner' | 'simple' ("More simplified": explained to a 15-year-old).
 * `previous` is the explanation the student found too hard, so the AI can
 * simplify it instead of starting from scratch.
 * Returns { line, error, level, explanation, source }.
 */
export async function explainError({ code, message, line, level = 'simple', previous = null }) {
  const res = await fetch(`${API_URL}/api/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, message, line, level, previous })
  })

  if (!res.ok) {
    throw new Error(`Couldn\u2019t get a simpler explanation (status ${res.status})`)
  }

  return res.json()
}
