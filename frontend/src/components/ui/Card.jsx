export function Card({ className = "", children, ...props }) {
  return (
    <div
      className={`bg-surface-container border border-surface-border rounded-2xl shadow-card ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
