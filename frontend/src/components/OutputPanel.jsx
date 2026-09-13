import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import AstNode from './AstTree.jsx'

const TABS = ['Output', 'Tokens', 'AST', 'Symbol Table', 'Errors & AI']

export default function OutputPanel({ result, loading, error }) {
  const [tab, setTab] = useState('Output')

  const errorCount = result?.errors?.length || 0

  return (
    <div className="output-pane">
      <div className="output-tabs">
        {TABS.map((t) => (
          <button
            key={t}
            className={`output-tab ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t}
            {t === 'Errors & AI' && errorCount > 0 && (
              <span className="badge">{errorCount}</span>
            )}
          </button>
        ))}
      </div>

      <div className="output-body">
        {loading && <div className="empty-state">Compiling…</div>}

        {!loading && error && (
          <div className="error-card">
            <div className="error-card-line">Request failed</div>
            <div className="error-card-message">{error}</div>
          </div>
        )}

        {!loading && !error && !result && (
          <div className="empty-state">Run your code to see results here.</div>
        )}

        {!loading && !error && result && tab === 'Output' && (
          result.output && result.output.length > 0 ? (
            result.output.map((line, i) => (
              <div key={i} className="output-line">{line}</div>
            ))
          ) : (
            <div className="empty-state">
              {result.errors?.length > 0
                ? 'Fix the errors below to run this program.'
                : 'No output — this program didn\u2019t print anything.'}
            </div>
          )
        )}

        {!loading && !error && result && tab === 'Tokens' && (
          result.tokens?.length > 0 ? (
            <table className="token-table">
              <thead>
                <tr><th>Type</th><th>Value</th><th>Line</th><th>Pos</th></tr>
              </thead>
              <tbody>
                {result.tokens.map((t, i) => (
                  <tr key={i}>
                    <td className="mono">{t.type}</td>
                    <td className="mono">{t.value}</td>
                    <td>{t.line}</td>
                    <td>{t.lexpos}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">No tokens yet.</div>
          )
        )}

        {!loading && !error && result && tab === 'AST' && (
          result.ast ? (
            <div className="ast-tree"><AstNode node={result.ast} /></div>
          ) : (
            <div className="empty-state">No AST — parsing failed before a tree could be built.</div>
          )
        )}

        {!loading && !error && result && tab === 'Symbol Table' && (
          result.symbol_table?.symbols?.length > 0 ? (
            <table className="symbol-table">
              <thead>
                <tr><th>Name</th><th>Type</th><th>Kind</th><th>Params</th></tr>
              </thead>
              <tbody>
                {result.symbol_table.symbols.map((s, i) => (
                  <tr key={i}>
                    <td className="mono">{s.name}</td>
                    <td className="mono">{s.type}</td>
                    <td>{s.kind}</td>
                    <td className="mono">
                      {s.params ? s.params.map((p) => p.join(': ')).join(', ') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state">
              No symbols — this shows top-level (global scope) declarations only.
            </div>
          )
        )}

        {!loading && !error && result && tab === 'Errors & AI' && (
          result.errors?.length > 0 ? (
            <>
              {result.errors.map((e, i) => (
                <div key={i} className="error-card">
                  <div className="error-card-line">Line {e.line}</div>
                  <div className="error-card-message">{e.message}</div>
                </div>
              ))}
              {result.ai_suggestions?.map((s, i) => (
                <div key={i} className="ai-card">
                  <div className="ai-card-title">AI explanation \u2014 line {s.line}</div>
                  <ReactMarkdown>{s.explanation}</ReactMarkdown>
                </div>
              ))}
            </>
          ) : (
            <div className="empty-state">No errors \u2014 nothing for the AI assistant to explain.</div>
          )
        )}
      </div>
    </div>
  )
}
