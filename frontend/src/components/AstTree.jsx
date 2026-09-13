// Renders the recursive { node_type, ...fields } structure returned by
// ASTNode.to_dict() on the backend.

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v)
}

function FieldValue({ name, value }) {
  if (isPlainObject(value) && value.node_type) {
    return (
      <div className="ast-node">
        <div>
          <span className="ast-field-name">{name}: </span>
          <AstNode node={value} />
        </div>
      </div>
    )
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return (
        <div>
          <span className="ast-field-name">{name}: </span>
          <span className="ast-leaf-value">[]</span>
        </div>
      )
    }
    return (
      <div className="ast-node">
        <span className="ast-field-name">{name}: [</span>
        {value.map((item, i) =>
          isPlainObject(item) && item.node_type ? (
            <AstNode key={i} node={item} />
          ) : (
            <div key={i} className="ast-leaf-value">{String(item)}</div>
          )
        )}
        <span className="ast-field-name">]</span>
      </div>
    )
  }

  return (
    <div>
      <span className="ast-field-name">{name}: </span>
      <span className="ast-leaf-value">{String(value)}</span>
    </div>
  )
}

export default function AstNode({ node }) {
  if (!node) return null
  const { node_type, ...fields } = node

  return (
    <div>
      <div className="ast-node-type">{node_type}</div>
      <div className="ast-node">
        {Object.entries(fields).map(([key, value]) => (
          <FieldValue key={key} name={key} value={value} />
        ))}
      </div>
    </div>
  )
}
