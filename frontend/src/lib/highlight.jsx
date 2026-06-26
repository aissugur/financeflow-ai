// highlightMatch — wrap the verbatim `match` substring inside `text` in a
// <mark>, so the UI can show *which* span of an evidence excerpt the question
// matched (Citation.match_text from the backend). Degrades gracefully:
//   - no match / not found  -> returns the plain text unchanged
//   - case-insensitive, but preserves the excerpt's original casing in output
// Returns a React-renderable node (string or array of strings + <mark>).
export function highlightMatch(text, match) {
  if (!text) return text ?? "";
  if (!match || typeof match !== "string") return text;

  const needle = match.trim();
  if (!needle) return text;

  const idx = text.toLowerCase().indexOf(needle.toLowerCase());
  if (idx === -1) return text; // span not present verbatim — show plain excerpt

  const before = text.slice(0, idx);
  const hit = text.slice(idx, idx + needle.length); // keep original casing
  const after = text.slice(idx + needle.length);

  return (
    <>
      {before}
      <mark className="evidence-mark">{hit}</mark>
      {after}
    </>
  );
}
