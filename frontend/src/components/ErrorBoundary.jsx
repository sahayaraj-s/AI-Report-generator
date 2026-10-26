import React from "react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("[ErrorBoundary] Uncaught application error:", error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoLogin = () => {
    window.location.href = "/login";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-surface flex items-center justify-center p-6 text-ink">
          <div className="w-full max-w-md bg-surface-dim border border-surface-border rounded-2xl p-6 shadow-xl text-center">
            <div className="h-12 w-12 rounded-2xl bg-danger/10 text-danger flex items-center justify-center mx-auto mb-4 font-bold text-xl">
              !
            </div>
            <h1 className="font-display font-semibold text-lg text-ink mb-2">
              Application Error
            </h1>
            <p className="text-xs text-ink-muted mb-4 leading-relaxed">
              An unexpected error occurred while loading this view. If you are deploying for the first time, check your environment variables in the hosting dashboard.
            </p>
            {this.state.error?.message && (
              <div className="bg-surface-container border border-surface-border rounded-xl p-3 mb-6 text-left overflow-x-auto text-[11px] font-mono text-danger">
                {this.state.error.message}
              </div>
            )}
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={this.handleReload}
                className="px-4 py-2 rounded-xl text-xs font-medium bg-brand-maroon text-white hover:bg-brand-maroon/90 transition-colors"
              >
                Reload Page
              </button>
              <button
                type="button"
                onClick={this.handleGoLogin}
                className="px-4 py-2 rounded-xl text-xs font-medium border border-surface-border text-ink hover:bg-surface-high transition-colors"
              >
                Go to Login
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
