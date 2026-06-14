// Shared UI states: LoadingState (shimmer), EmptyState, ErrorState, SuccessNote.
import { IconAlert, IconInbox } from "../../lib/icons";

export function LoadingState({ lines = 3, label }) {
  return (
    <div>
      {label && <p className="muted" style={{ marginBottom: 12, fontSize: 13 }}>{label}</p>}
      <div className="skeleton">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            className="sk-line"
            key={i}
            style={{ width: `${100 - i * 12}%` }}
          />
        ))}
      </div>
    </div>
  );
}

export function EmptyState({ title, children, icon }) {
  return (
    <div className="empty">
      <div className="empty-ico">{icon || <IconInbox />}</div>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </div>
  );
}

export function ErrorState({ children }) {
  if (!children) return null;
  return (
    <div className="errorbox">
      <IconAlert size={16} />
      <span>{children}</span>
    </div>
  );
}

export function SuccessNote({ children }) {
  if (!children) return null;
  return <div className="successbox">✓ <span>{children}</span></div>;
}
