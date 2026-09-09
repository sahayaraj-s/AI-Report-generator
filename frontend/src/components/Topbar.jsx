import { useState, useRef, useEffect } from "react";
import { Search, Bell, Sun, Moon, Upload, Activity, X, ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { api } from "../lib/api";

function timeAgo(isoString) {
  if (!isoString) return "";
  const diff = (Date.now() - new Date(isoString + "Z").getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function Topbar({ title, subtitle }) {
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const initial = (user?.displayName || user?.email || "A").charAt(0).toUpperCase();

  const [searchVal, setSearchVal] = useState("");
  const [bellOpen, setBellOpen] = useState(false);
  const bellRef = useRef(null);

  // Close bell on outside click
  useEffect(() => {
    function handleClick(e) {
      if (bellRef.current && !bellRef.current.contains(e.target)) {
        setBellOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Notifications query
  const { data: notifData } = useQuery({
    queryKey: ["notifications"],
    queryFn: async () => (await api.get("/api/admin/notifications")).data,
    refetchInterval: 30000,
  });

  const notifications = notifData?.notifications || [];

  const handleSearch = (e) => {
    e.preventDefault();
    const q = searchVal.trim();
    if (q) {
      navigate(`/students?search=${encodeURIComponent(q)}`);
      setSearchVal("");
    }
  };

  const handleSearchKeyDown = (e) => {
    if (e.key === "Enter") handleSearch(e);
  };

  return (
    <header className="h-16 border-b border-surface-border bg-surface/80 backdrop-blur sticky top-0 z-10 flex items-center justify-between px-6 gap-4">
      <div className="min-w-0">
        <h1 className="text-lg font-display font-semibold text-ink truncate">{title}</h1>
        {subtitle && <p className="text-xs text-ink-faint truncate">{subtitle}</p>}
      </div>

      {/* Search Box */}
      <div className="flex-1 max-w-md hidden md:block">
        <form onSubmit={handleSearch}>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint pointer-events-none" />
            <input
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              onKeyDown={handleSearchKeyDown}
              placeholder="Search students by name, roll number…"
              className="w-full bg-surface-container border border-surface-border rounded-xl pl-9 pr-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand-maroon/40 transition-all"
            />
            {searchVal && (
              <button
                type="button"
                onClick={() => setSearchVal("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-faint hover:text-ink"
              >
                <X size={13} />
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === "light" ? "Dark" : "Light"} Mode`}
          className="h-9 px-3 rounded-xl bg-surface-container border border-surface-border flex items-center gap-2 text-xs font-medium text-ink-muted hover:text-ink transition-colors"
        >
          {theme === "light" ? (
            <>
              <Moon size={16} className="text-brand-purple" />
              <span className="hidden sm:inline">Dark</span>
            </>
          ) : (
            <>
              <Sun size={16} className="text-brand-yellow" />
              <span className="hidden sm:inline">Light</span>
            </>
          )}
        </button>

        {/* Notification Bell */}
        <div className="relative" ref={bellRef}>
          <button
            onClick={() => setBellOpen((o) => !o)}
            className="relative h-9 w-9 rounded-xl bg-surface-container border border-surface-border flex items-center justify-center text-ink-muted hover:text-ink transition-colors"
            title="Notifications"
          >
            <Bell size={17} />
            {notifications.length > 0 && (
              <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-brand-maroon text-white text-[9px] font-bold flex items-center justify-center">
                {Math.min(notifications.length, 9)}
              </span>
            )}
          </button>

          {/* Notification Panel */}
          {bellOpen && (
            <div className="absolute right-0 top-11 w-80 bg-surface-dim border border-surface-border rounded-2xl shadow-2xl overflow-hidden z-50">
              <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border">
                <span className="font-semibold text-sm text-ink">Notifications</span>
                <button onClick={() => setBellOpen(false)} className="text-ink-faint hover:text-ink">
                  <X size={14} />
                </button>
              </div>

              <div className="max-h-72 overflow-y-auto divide-y divide-surface-border">
                {notifications.length === 0 ? (
                  <div className="py-8 text-center text-ink-faint text-sm">No notifications yet.</div>
                ) : (
                  notifications.map((n) => (
                    <div key={n.id} className="flex items-start gap-3 px-4 py-3 hover:bg-surface-high/50 transition-colors">
                      <div className={`mt-0.5 h-7 w-7 rounded-lg flex items-center justify-center shrink-0 ${
                        n.type === "upload" ? "bg-brand-maroon/10 text-brand-maroon" : "bg-brand-purple/10 text-brand-purple"
                      }`}>
                        {n.type === "upload" ? <Upload size={13} /> : <Activity size={13} />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-xs font-semibold text-ink truncate">{n.title}</div>
                        {n.body && <div className="text-[11px] text-ink-faint mt-0.5 truncate">{n.body}</div>}
                        <div className="text-[10px] text-ink-faint mt-1">{timeAgo(n.time)}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="border-t border-surface-border px-4 py-2.5">
                <button
                  onClick={() => { navigate("/upload"); setBellOpen(false); }}
                  className="text-xs text-brand-maroon hover:text-brand-pink font-medium flex items-center gap-1 w-full justify-center"
                >
                  Upload New Batch <ChevronRight size={12} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User avatar */}
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-full bg-brand-maroon flex items-center justify-center text-white text-sm font-semibold">
            {initial}
          </div>
          <div className="text-xs leading-tight hidden sm:block">
            <div className="text-ink font-medium">{user?.displayName || "Admin"}</div>
            <div className="text-ink-faint">SUPERUSER</div>
          </div>
        </div>
      </div>
    </header>
  );
}
