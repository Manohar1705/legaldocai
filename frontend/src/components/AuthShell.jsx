export default function AuthShell({ tagline, children }) {
  return (
    <div className="auth-page">
      <div className="auth-shell">
        <div className="auth-brand">
          <p className="wordmark">LegalDocAI</p>
          {tagline && <p className="tagline">{tagline}</p>}
        </div>
        <div className="auth-card">{children}</div>
      </div>
    </div>
  );
}
