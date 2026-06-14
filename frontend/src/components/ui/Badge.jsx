// Badge — tone: accent | success | warn | danger (default neutral). dot adds a marker.
export default function Badge({ tone, dot, children, className = "" }) {
  const classes = ["badge", tone && `badge--${tone}`, className]
    .filter(Boolean)
    .join(" ");
  return (
    <span className={classes}>
      {dot && <span className="dot" aria-hidden />}
      {children}
    </span>
  );
}
