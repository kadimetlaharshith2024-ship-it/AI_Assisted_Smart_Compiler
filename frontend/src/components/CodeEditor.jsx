import { useMemo, useRef, useEffect } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { javascript } from '@codemirror/lang-javascript'
import { oneDark } from '@codemirror/theme-one-dark'
import { StateField, StateEffect } from '@codemirror/state'
import { Decoration, EditorView } from '@codemirror/view'

// Lumen's syntax (let/fn/->/foreach/etc.) is close enough to JS/TS for
// CodeMirror's JS grammar to give reasonable highlighting without writing
// a dedicated language package for a college demo.

const setErrorLines = StateEffect.define()

const errorLineField = StateField.define({
  create() {
    return Decoration.none
  },
  update(decorations, tr) {
    decorations = decorations.map(tr.changes)
    for (const effect of tr.effects) {
      if (effect.is(setErrorLines)) {
        const lineNumbers = effect.value
        const ranges = []
        for (const ln of lineNumbers) {
          if (ln >= 1 && ln <= tr.state.doc.lines) {
            const line = tr.state.doc.line(ln)
            ranges.push(
              Decoration.line({ attributes: { class: 'cm-error-line' } }).range(line.from)
            )
          }
        }
        decorations = Decoration.set(ranges, true)
      }
    }
    return decorations
  },
  provide: (f) => EditorView.decorations.from(f)
})

const errorLineTheme = EditorView.baseTheme({
  '.cm-error-line': {
    backgroundColor: 'rgba(232, 100, 106, 0.12)',
    borderLeft: '2px solid #e8646a'
  }
})

export default function CodeEditor({ value, onChange, errorLines = [] }) {
  const viewRef = useRef(null)

  const extensions = useMemo(
    () => [javascript(), errorLineField, errorLineTheme],
    []
  )

  useEffect(() => {
    const view = viewRef.current
    if (view) {
      view.dispatch({ effects: setErrorLines.of(errorLines) })
    }
  }, [errorLines])

  return (
    <CodeMirror
      value={value}
      height="100%"
      theme={oneDark}
      extensions={extensions}
      onChange={onChange}
      basicSetup={{ lineNumbers: true, foldGutter: false, highlightActiveLine: true }}
      onCreateEditor={(view) => {
        viewRef.current = view
        view.dispatch({ effects: setErrorLines.of(errorLines) })
      }}
    />
  )
}
