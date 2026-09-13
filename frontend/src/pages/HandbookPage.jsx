import { useState } from 'react'
import { lessons } from '../data/handbookContent.js'

function ExampleBlock({ example, onRun }) {
  return (
    <div className="example-block">
      <div className="example-block-header">
        <span className="example-block-label">{example.label}</span>
        <button className="run-example-btn" onClick={() => onRun(example.code)}>
          Run in Playground
        </button>
      </div>
      <pre>{example.code}</pre>
    </div>
  )
}

function LessonBody({ lesson, onRun }) {
  return (
    <div className="lesson-content-inner">
      <h2>{lesson.title}</h2>
      {lesson.intro && <p>{lesson.intro}</p>}

      {lesson.typeTable && (
        <table className="type-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Example literal</th>
              <th>Default value</th>
            </tr>
          </thead>
          <tbody>
            {lesson.typeTable.map((row) => (
              <tr key={row.type}>
                <td className="mono">{row.type}</td>
                <td className="mono">{row.literal}</td>
                <td className="mono">{row.default}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {lesson.examples &&
        lesson.examples.map((ex) => (
          <ExampleBlock key={ex.label} example={ex} onRun={onRun} />
        ))}

      {lesson.subsections &&
        lesson.subsections.map((sub) => (
          <div key={sub.heading}>
            <h3 style={{ fontSize: '1.05rem', marginTop: '28px', color: 'var(--text)' }}>
              {sub.heading}
            </h3>
            {sub.body && <p>{sub.body}</p>}
            {sub.examples.map((ex) => (
              <ExampleBlock key={ex.label} example={ex} onRun={onRun} />
            ))}
          </div>
        ))}

      {lesson.keywords && (
        <div className="keyword-chip-row">
          {lesson.keywords.map((kw) => (
            <span className="keyword-chip" key={kw}>{kw}</span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function HandbookPage({ onRun }) {
  const [activeId, setActiveId] = useState(lessons[0].id)
  const activeLesson = lessons.find((l) => l.id === activeId)

  return (
    <div className="handbook-layout">
      <nav className="lesson-rail">
        {lessons.map((lesson) => (
          <button
            key={lesson.id}
            className={`lesson-item ${lesson.id === activeId ? 'active' : ''}`}
            onClick={() => setActiveId(lesson.id)}
          >
            <span className="lesson-number">{lesson.number}</span>
            <span>{lesson.title}</span>
          </button>
        ))}
      </nav>
      <div className="lesson-content">
        <LessonBody lesson={activeLesson} onRun={onRun} />
      </div>
    </div>
  )
}
