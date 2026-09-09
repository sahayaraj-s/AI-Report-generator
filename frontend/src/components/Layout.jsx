import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import MiniChatbot from "./MiniChatbot";

export function Layout({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="flex-1 min-w-0">
        <Topbar title={title} subtitle={subtitle} />
        <main className="p-6 max-w-[1600px] mx-auto">{children}</main>
      </div>
      <MiniChatbot />
    </div>
  );
}
