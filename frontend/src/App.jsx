import { useState } from 'react'
import HandbookPage from './pages/HandbookPage.jsx'
import Playground from './pages/Playground.jsx'

export default function App() {
  const [mode, setMode] = useState('handbook') // 'handbook' | 'playground'
  // Code queued up from a handbook "Run in Playground" click, consumed
  // by Playground on mount/update then cleared.
  const [pendingCode, setPendingCode] = useState(null)

  function runInPlayground(code) {
    setPendingCode(code)
    setMode('playground')
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="wordmark">
          Lumen<span className="dot">.</span>
        </div>
        <nav className="mode-tabs">
          <button
            className={`mode-tab ${mode === 'handbook' ? 'active' : ''}`}
            onClick={() => setMode('handbook')}
          >
            Handbook
          </button>
          <button
            className={`mode-tab ${mode === 'playground' ? 'active' : ''}`}
            onClick={() => setMode('playground')}
          >
            Playground
          </button>
        </nav>
      </header>

      <div className="app-body">
        {mode === 'handbook' && <HandbookPage onRun={runInPlayground} />}
        {mode === 'playground' && (
          <Playground
            pendingCode={pendingCode}
            onPendingConsumed={() => setPendingCode(null)}
          />
        )}
      </div>
    </div>
  )
}
