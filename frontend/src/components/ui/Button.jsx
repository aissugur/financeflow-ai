// Button — variants: primary | ghost | danger (default neutral). Sizes: sm | lg.
export default function Button({
  variant = "neutral",
  size,
  block,
  loading = false,
  children,
  className = "",
  disabled,
  ...rest
}) {
  const classes = [
    "btn",
    variant === "primary" && "btn--primary",
    variant === "ghost" && "btn--ghost",
    variant === "danger" && "btn--danger",
    size === "sm" && "btn--sm",
    size === "lg" && "btn--lg",
    block && "btn--block",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classes} disabled={disabled || loading} {...rest}>
      {loading && <span className="spin" aria-hidden />}
      {children}
    </button>
  );
}
