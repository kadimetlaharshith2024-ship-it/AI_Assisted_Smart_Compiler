import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { explainError } from '../api.js'

/**
 * One AI explanation card.
 *
 * - Shows the beginner-friendly explanation first. "More simplified" asks the
 *   backend to re-explain the same error as if to a 15-year-old who just started
 *   coding; that text is fetched once and kept, so toggling is instant.
 * - When the backend verified an AI-proposed fix (it compiled the fixed program),
 *   the card shows what changes and an "Apply fix" button. `fix` is null when
 *   there is no fix or it failed verification.
 */
export default function AiSuggestion({ suggestion, code, onApplyFix, editorChanged }) {
  const [view, setView] = useState('beginner') // 'beginner' | 'simple'
  const [simple, setSimple] = useState(null)   // { explanation, source } once fetched
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(null)
  const [applied, setApplied] = useState(false)

  async function showSimpler() {
    setFailed(null)
    if (simple) {
      setView('simple')
      return
    }
    setLoading(true)
    try {
      const data = await explainError({
        code,
        message: suggestion.error,
        line: suggestion.line,
        level: 'simple',
        previous: suggestion.explanation
      })
      setSimple(data)
      setView('simple')
    } catch (err) {
      setFailed(err.message)
    } finally {
      setLoading(false)
    }
  }

  function applyFix() {
    onApplyFix(suggestion.fix.code)
    setApplied(true)
  }

  const showingSimple = view === 'simple' && simple
  const text = showingSimple ? simple.explanation : suggestion.explanation
  const source = showingSimple ? simple.source : suggestion.source
  const fix = suggestion.fix

  return (
    <div className="ai-card">
      <div className="ai-card-header">
        <span className="ai-card-title">
          {suggestion.line > 0 ? `AI explanation \u2014 line ${suggestion.line}` : 'AI explanation'}
        </span>
        {showingSimple && <span className="ai-tag simple">Simplified</span>}
        {source === 'offline' && (
          <span className="ai-tag" title="No AI key is configured, so this is a built-in explanation.">
            Built-in tips
          </span>
        )}
      </div>

      <ReactMarkdown>{text}</ReactMarkdown>

      {fix && (
        <div className="ai-fix">
          <div className="ai-fix-header">
            <span
              className="ai-fix-badge"
              title="The compiler checked this fix: the error is gone and no new errors appeared. It does not prove the program does what you intended."
            >
              {'\u2713'} Verified fix
            </span>
            <span className="ai-fix-note">
              {fix.resolves_all
                ? 'The program compiles with no errors.'
                : 'Fixes this error; other errors may remain.'}
            </span>
          </div>

          {fix.changes.map((change, i) => (
            <div key={i} className="ai-fix-change">
              <div className="ai-fix-where">
                {change.before.length > 0 ? `Line ${change.line}` : `Added near line ${change.line}`}
              </div>
              {change.before.map((l, j) => (
                <div key={`b${j}`} className="diff-line del">- {l}</div>
              ))}
              {change.after.map((l, j) => (
                <div key={`a${j}`} className="diff-line add">+ {l}</div>
              ))}
            </div>
          ))}

          <div className="ai-fix-actions">
            {applied ? (
              <span className="ai-fix-note">{'\u2713'} Applied to the editor — press Run to check it.</span>
            ) : (
              <button
                className="ai-simplify-btn"
                onClick={applyFix}
                disabled={editorChanged}
                title={editorChanged ? 'The editor changed since this run. Run again to get a fresh fix.' : undefined}
              >
                {editorChanged ? 'Editor changed \u2014 run again' : 'Apply fix'}
              </button>
            )}
          </div>
        </div>
      )}

      <div className="ai-card-actions">
        {showingSimple ? (
          <button className="ai-simplify-btn subtle" onClick={() => setView('beginner')}>
            {'\u2190'} Back to the normal explanation
          </button>
        ) : (
          <button className="ai-simplify-btn" onClick={showSimpler} disabled={loading}>
            {loading ? 'Simplifying\u2026' : '\u2728 More simplified'}
          </button>
        )}
        {failed && <span className="ai-card-error">{failed}</span>}
      </div>
    </div>
  )
}
