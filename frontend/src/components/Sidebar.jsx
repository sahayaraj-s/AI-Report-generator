import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  UploadCloud,
  Users,
  Briefcase,
  Sparkles,
  Settings,
  LogOut,
  Sun,
  Moon,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/upload", label: "Upload Excel", icon: UploadCloud },
  { to: "/students", label: "Students", icon: Users },
  { to: "/jobs", label: "Job Roles", icon: Briefcase },
  { to: "/ai-assistant", label: "SkillBay AI", icon: Sparkles },
];

export function Sidebar() {
  const { logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <aside className="w-60 shrink-0 border-r border-surface-border bg-surface-dim flex flex-col h-screen sticky top-0">
      <div className="flex items-center gap-2.5 px-5 h-16 border-b border-surface-border">
        <img src="/logo.png" alt="Skill Bay Academy" className="h-8 w-8 rounded-lg object-cover" />
        <div className="leading-tight">
          <div className="font-display font-semibold text-sm text-ink">Skill Bay Academy</div>
          <div className="text-[10px] text-brand-pink font-medium flex items-center gap-1">
            <span>Kauvery Hospital</span>
            <span className="text-ink-faint">· CCDP</span>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                isActive
                  ? "bg-brand-maroon/15 text-brand-pink"
                  : "text-ink-muted hover:text-ink hover:bg-surface-high"
              }`
            }
          >
            <Icon size={18} />
            {label}
            {label === "SkillBay AI" && (
              <span className="ml-auto text-[10px] bg-brand-maroon/20 text-brand-pink px-1.5 py-0.5 rounded-full font-medium">
                AI
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-surface-border space-y-1">
        <button
          onClick={toggleTheme}
          className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium text-ink-muted hover:text-ink hover:bg-surface-high transition-colors"
        >
          <div className="flex items-center gap-3">
            {theme === "light" ? <Moon size={18} className="text-brand-purple" /> : <Sun size={18} className="text-brand-yellow" />}
            <span>Theme</span>
          </div>
          <span className="text-xs text-ink-faint capitalize">{theme}</span>
        </button>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
              isActive
                ? "bg-brand-maroon/15 text-brand-pink"
                : "text-ink-muted hover:text-ink hover:bg-surface-high"
            }`
          }
        >
          <Settings size={18} />
          Settings
        </NavLink>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-ink-muted hover:text-danger hover:bg-danger/10 transition-colors"
        >
          <LogOut size={18} />
          Logout
        </button>
      </div>
    </aside>
  );
}
