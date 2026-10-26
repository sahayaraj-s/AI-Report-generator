import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import {
  Lock,
  Mail,
  Eye,
  EyeOff,
  ArrowRight,
  Sun,
  Moon,
  Building2,
  ShieldCheck,
  KeyRound,
  AlertCircle,
} from "lucide-react";

export default function Login() {
  const {
    user,
    loginWithGoogle,
    loginWithEmail,
    authError,
  } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showForgotModal, setShowForgotModal] = useState(false);

  // If already authenticated, redirect to dashboard
  if (user) return <Navigate to="/" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Please enter both email and password.");
      return;
    }

    setBusy(true);
    try {
      await loginWithEmail(email.trim(), password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Invalid email or password. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  const handleGoogle = async () => {
    setError("");
    setBusy(true);
    try {
      await loginWithGoogle();
      navigate("/");
    } catch (err) {
      setError(err.message || "Google sign-in failed. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex flex-col justify-between relative overflow-hidden transition-colors selection:bg-brand-maroon selection:text-white">
      {/* Subtle background ambient accents */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-brand-maroon/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 -right-40 w-96 h-96 bg-brand-purple/10 rounded-full blur-3xl pointer-events-none" />

      {/* Top Navigation */}
      <header className="relative z-10 w-full max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img
            src="/logo.png"
            alt="Skill Bay Academy"
            className="h-9 w-9 rounded-xl object-cover shadow-sm ring-1 ring-surface-border"
          />
          <div>
            <div className="font-display font-semibold text-sm text-ink leading-tight">
              Skill Bay Academy
            </div>
            <div className="text-[11px] text-ink-faint flex items-center gap-1">
              <Building2 size={11} className="text-brand-purple" />
              Kauvery Hospital • CCDP
            </div>
          </div>
        </div>

        <button
          onClick={toggleTheme}
          type="button"
          className="p-2 rounded-xl border border-surface-border bg-surface-dim hover:bg-surface-high text-ink-muted hover:text-ink transition-colors shadow-sm"
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        >
          {theme === "light" ? (
            <Moon size={17} className="text-brand-purple" />
          ) : (
            <Sun size={17} className="text-brand-yellow" />
          )}
        </button>
      </header>

      {/* Main Login Box */}
      <main className="relative z-10 flex-1 flex items-center justify-center p-6 my-auto">
        <div className="w-full max-w-md">
          {/* Header */}
          <div className="text-center mb-6">
            <h1 className="font-display font-bold text-2xl sm:text-3xl text-ink tracking-tight">
              Welcome back
            </h1>
            <p className="text-sm text-ink-muted mt-1.5">
              Sign in to access your placement analytics dashboard
            </p>
          </div>

          {/* Clean Card */}
          <div className="rounded-2xl border border-surface-border bg-surface-dim/90 backdrop-blur-xl shadow-xl p-6 sm:p-8 transition-all">
            {/* Error Message */}
            {(error || authError) && (
              <div className="mb-5 rounded-xl border border-danger/30 bg-danger/10 p-3 text-xs text-danger flex items-start gap-2.5 animate-fadeIn">
                <AlertCircle size={16} className="shrink-0 mt-0.5" />
                <div className="flex-1">{error || authError}</div>
              </div>
            )}

            {/* Email & Password Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-ink-muted mb-1.5 block">
                  Email Address
                </label>
                <div className="relative">
                  <Mail
                    size={16}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint"
                  />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-surface-container border border-surface-border rounded-xl pl-10 pr-3 py-2.5 text-sm text-ink placeholder:text-ink-faint/60 focus:outline-none focus:ring-2 focus:ring-brand-maroon/40 focus:border-brand-maroon transition-all"
                    placeholder="name@skillbayacademy.com"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-ink-muted">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowForgotModal(true)}
                    className="text-xs text-brand-pink hover:underline font-medium"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <Lock
                    size={16}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint"
                  />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-surface-container border border-surface-border rounded-xl pl-10 pr-10 py-2.5 text-sm text-ink placeholder:text-ink-faint/60 focus:outline-none focus:ring-2 focus:ring-brand-maroon/40 focus:border-brand-maroon transition-all"
                    placeholder="••••••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint hover:text-ink transition-colors p-1"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 text-xs text-ink-muted cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-surface-border text-brand-maroon focus:ring-brand-maroon/30 w-4 h-4 cursor-pointer"
                  />
                  Remember me
                </label>
              </div>

              {/* Primary Sign In Button */}
              <button
                type="submit"
                disabled={busy}
                className="w-full mt-2 flex items-center justify-center gap-2 rounded-xl bg-brand-maroon hover:bg-brand-maroon/90 text-white font-medium py-2.5 text-sm shadow-sm transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50"
              >
                {busy ? (
                  <span>Signing in…</span>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="flex items-center gap-3 my-5">
              <div className="h-px bg-surface-border flex-1" />
              <span className="text-[11px] uppercase tracking-wider text-ink-faint">
                or
              </span>
              <div className="h-px bg-surface-border flex-1" />
            </div>

            {/* Google Sign In */}
            <button
              type="button"
              onClick={handleGoogle}
              disabled={busy}
              className="w-full flex items-center justify-center gap-2.5 rounded-xl border border-surface-border bg-surface-high hover:bg-surface-container py-2.5 text-xs font-medium text-ink hover:text-ink transition-all shadow-sm disabled:opacity-50"
            >
              <svg width="16" height="16" viewBox="0 0 18 18">
                <path
                  fill="#4285F4"
                  d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.56 2.7-3.87 2.7-6.62Z"
                />
                <path
                  fill="#34A853"
                  d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.98v2.33A9 9 0 0 0 9 18Z"
                />
                <path
                  fill="#FBBC05"
                  d="M3.95 10.7A5.4 5.4 0 0 1 3.67 9c0-.59.1-1.17.28-1.7V4.96H.98A9 9 0 0 0 0 9c0 1.45.35 2.83.98 4.04l2.97-2.33Z"
                />
                <path
                  fill="#EA4335"
                  d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .98 4.96l2.97 2.33C4.66 5.17 6.65 3.58 9 3.58Z"
                />
              </svg>
              <span>Sign in with Google</span>
            </button>
          </div>

          {/* Clean Security Note */}
          <div className="text-center mt-5">
            <p className="text-xs text-ink-faint flex items-center justify-center gap-1.5">
              <ShieldCheck size={14} className="text-emerald-500" />
              Secure encrypted placement platform
            </p>
          </div>
        </div>
      </main>

      {/* Clean Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="w-full max-w-sm rounded-2xl bg-surface-dim border border-surface-border p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-brand-maroon/15 text-brand-pink">
                <KeyRound size={20} />
              </div>
              <div>
                <h3 className="font-display font-semibold text-base text-ink">
                  Reset Password
                </h3>
                <p className="text-xs text-ink-faint">Account Support</p>
              </div>
            </div>
            <p className="text-xs text-ink-muted leading-relaxed mb-5">
              Please contact your Placement Administrator or email{" "}
              <span className="text-brand-pink font-medium">support@skillbayacademy.com</span>{" "}
              to request a password reset for your account.
            </p>
            <button
              onClick={() => setShowForgotModal(false)}
              className="w-full py-2.5 rounded-xl bg-surface-high hover:bg-surface-container text-ink font-medium text-xs transition-colors"
            >
              Got it
            </button>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="relative z-10 w-full max-w-6xl mx-auto px-6 py-4 flex flex-col sm:flex-row items-center justify-between text-xs text-ink-faint gap-2 border-t border-surface-border/50">
        <div>
          © {new Date().getFullYear()} Skill Bay Academy. All rights reserved.
        </div>
        <div className="flex items-center gap-3">
          <span>Kauvery Hospital CCDP</span>
          <span>•</span>
          <span>Privacy & Terms</span>
        </div>
      </footer>
    </div>
  );
}
