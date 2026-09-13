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
