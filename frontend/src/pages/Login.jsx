import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";

export default function Login() {
  const { user, loginWithGoogle, loginWithEmail } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const handleGoogle = async () => {
    setError("");
    setBusy(true);
    try {
      await loginWithGoogle();
      navigate("/");
    } catch (err) {
      setError(err.message || "Google sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  const handleEmail = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await loginWithEmail(email, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <img src="/logo.png" alt="Skill Bay Academy" className="h-16 w-16 rounded-2xl object-cover mb-4" />
          <h1 className="font-display font-semibold text-xl text-ink">Skill Bay Academy</h1>
          <p className="text-sm text-ink-faint mt-1">Placement Analytics — Admin Login</p>
        </div>

        <Card className="p-6">
          <button
            onClick={handleGoogle}
            disabled={busy}
            className="w-full flex items-center justify-center gap-2 rounded-xl border border-surface-border bg-surface-high py-2.5 text-sm font-medium text-ink hover:bg-surface-container transition-colors disabled:opacity-50"
          >
            <svg width="18" height="18" viewBox="0 0 18 18">
              <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.56 2.7-3.87 2.7-6.62Z" />
              <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.98v2.33A9 9 0 0 0 9 18Z" />
              <path fill="#FBBC05" d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.96H.98A9 9 0 0 0 0 9c0 1.45.35 2.83.98 4.04l2.97-2.33Z" />
              <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .98 4.96l2.97 2.33C4.66 5.17 6.65 3.58 9 3.58Z" />
            </svg>
            Sign in with Google
          </button>

          <div className="flex items-center gap-3 my-5">
            <div className="h-px bg-surface-border flex-1" />
            <span className="text-xs text-ink-faint">or</span>
            <div className="h-px bg-surface-border flex-1" />
          </div>

          <form onSubmit={handleEmail} className="space-y-3">
            <div>
              <label className="text-xs text-ink-muted mb-1 block">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                placeholder="admin@skillbayacademy.com"
              />
            </div>
            <div>
              <label className="text-xs text-ink-muted mb-1 block">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2.5 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                placeholder="••••••••"
              />
            </div>

            <div className="flex items-center justify-between text-xs">
              <label className="flex items-center gap-2 text-ink-muted">
                <input type="checkbox" className="rounded border-surface-border" />
                Remember me
              </label>
              <button type="button" className="text-brand-pink hover:underline">
                Forgot password?
              </button>
            </div>

            {error && <p className="text-xs text-danger">{error}</p>}

            <Button type="submit" disabled={busy} className="w-full mt-2">
              {busy ? "Signing in…" : "Sign In"}
            </Button>
          </form>
        </Card>

        <p className="text-center text-xs text-ink-faint mt-5">
          Access restricted to authorized institute administrators.
        </p>
      </div>
    </div>
  );
}
