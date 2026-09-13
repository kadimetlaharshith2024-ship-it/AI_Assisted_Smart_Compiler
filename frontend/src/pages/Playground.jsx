import { useState, useEffect, useCallback } from 'react'
import CodeEditor from '../components/CodeEditor.jsx'
import OutputPanel from '../components/OutputPanel.jsx'
import { compileCode } from '../api.js'

const DEFAULT_CODE = `fn factorial(n: int) -> int {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

let result: int = factorial(6);
print(result);
`

export default function Playground({ pendingCode, onPendingConsumed }) {
  const [code, setCode] = useState(DEFAULT_CODE)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [requestError, setRequestError] = useState(null)

  useEffect(() => {
    if (pendingCode != null) {
      setCode(pendingCode)
      onPendingConsumed()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingCode])

  const run = useCallback(async () => {
    setLoading(true)
    setRequestError(null)
    try {
      const data = await compileCode(code)
      setResult(data)
    } catch (err) {
      setRequestError(err.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [code])

  // Cmd/Ctrl+Enter to run, since that's the muscle memory from every other
  // in-browser code tool.
  useEffect(() => {
    function handler(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault()
        run()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [run])

  const errorLines = result?.errors?.map((e) => e.line).filter((l) => l > 0) || []

  let statusDot = 'pending'
  let statusText = 'Ready'
  if (loading) {
    statusDot = 'pending'
    statusText = 'Compiling…'
  } else if (requestError) {
    statusDot = 'err'
    statusText = `Couldn\u2019t reach the backend \u2014 ${requestError}`
  } else if (result) {
    if (result.errors?.length > 0) {
      statusDot = 'err'
      statusText = `${result.errors.length} error${result.errors.length > 1 ? 's' : ''}`
    } else {
      statusDot = 'ok'
      statusText = 'Compiled successfully'
    }
  }

  return (
    <div className="playground-layout">
      <div className="editor-pane">
        <div className="editor-toolbar">
          <span className="editor-toolbar-label">source.lumen</span>
          <button className="run-btn" onClick={run} disabled={loading}>
            {loading ? 'Running…' : 'Run \u25b8'}
          </button>
        </div>
        <div className="editor-wrap">
          <CodeEditor value={code} onChange={setCode} errorLines={errorLines} />
        </div>
        <div className="status-strip">
          <span className={`status-dot ${statusDot}`} />
          <span>{statusText}</span>
        </div>
      </div>
      <OutputPanel result={result} loading={loading} error={requestError} />
    </div>
  )
}
