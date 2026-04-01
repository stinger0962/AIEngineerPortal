import { Header } from "@/components/layout/header";
import { SidebarNav } from "@/components/layout/sidebar-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(247,127,0,0.18),_transparent_24%),linear-gradient(135deg,_#f8f3e8,_#eef5f1_58%,_#f7efe5)] text-ink">
      <div className="mx-auto flex max-w-[1600px]">
        <SidebarNav />
        <main className="min-h-screen flex-1 px-4 py-4 pt-16 lg:px-8 lg:py-6 lg:pt-6">
          <div className="space-y-8">
            <Header />
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
