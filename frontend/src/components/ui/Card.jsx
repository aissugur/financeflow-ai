// Card — rounded surface panel. Props: glass, hover.
export default function Card({ glass, hover, className = "", children, ...rest }) {
  const classes = [
    "card",
    glass && "card--glass",
    hover && "card--hover",
    className,
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}
