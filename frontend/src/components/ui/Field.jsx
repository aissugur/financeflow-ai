// Field primitives: labelled Textarea and Select wrappers.
export function Textarea({ label, error, id, className = "", ...rest }) {
  const errId = error && id ? `${id}-err` : error ? "field-err" : undefined;
  return (
    <label className="field">
      {label && <span className="field-label">{label}</span>}
      <textarea
        id={id}
        className={`textarea ${className}`}
        aria-invalid={error ? true : undefined}
        aria-describedby={errId}
        {...rest}
      />
      {error && (
        <span className="field-error" id={errId} role="alert">
          {error}
        </span>
      )}
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
