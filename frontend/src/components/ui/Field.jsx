// Field primitives: labelled Textarea and Select wrappers.
export function Textarea({ label, className = "", ...rest }) {
  return (
    <label className="field">
      {label && <span className="field-label">{label}</span>}
      <textarea className={`textarea ${className}`} {...rest} />
    </label>
  );
}

export function Select({ label, children, className = "", ...rest }) {
  return (
    <label className="field">
      {label && <span className="field-label">{label}</span>}
      <select className={`select ${className}`} {...rest}>
        {children}
      </select>
    </label>
  );
}
