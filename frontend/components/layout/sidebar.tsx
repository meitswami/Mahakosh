"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  ScanText,
  BookOpen,
  Calculator,
  GitBranch,
  MessageSquare,
  BarChart3,
  Settings,
  ChevronLeft,
  Sparkles,
  Bot,
  Radio,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/store/ui-store";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const navigation = [
  { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { title: "Documents", href: "/documents", icon: FileText },
  { title: "OCR Intelligence", href: "/ocr", icon: ScanText },
  { title: "Knowledge Base", href: "/knowledge", icon: BookOpen },
  { title: "Accounting Center", href: "/accounting", icon: Calculator },
  { title: "Agent Swarm", href: "/agents", icon: Bot },
  { title: "Workflows", href: "/workflows", icon: GitBranch },
  { title: "AI Chat", href: "/chat", icon: MessageSquare },
  { title: "Channels", href: "/channels", icon: Radio },
  { title: "Reports", href: "/reports", icon: BarChart3 },
];

const bottomNavigation = [
  { title: "Administration", href: "/admin", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-sidebar-border bg-sidebar transition-all duration-300",
        sidebarCollapsed ? "w-[68px]" : "w-[260px]",
      )}
    >
      <div className="flex h-16 items-center gap-3 px-4">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Sparkles className="h-5 w-5" />
        </div>
        {!sidebarCollapsed && (
          <div className="flex flex-col">
            <span className="font-display text-base font-semibold tracking-tight text-sidebar-foreground">
              Mahakosh
            </span>
            <span className="text-[11px] text-muted-foreground">ज्ञान से निर्णय तक</span>
          </div>
        )}
      </div>

      <Separator />

      <nav className="flex-1 space-y-1 p-3">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground",
                sidebarCollapsed && "justify-center px-2",
              )}
            >
              <Icon className="h-[18px] w-[18px] shrink-0" />
              {!sidebarCollapsed && <span>{item.title}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="space-y-1 p-3">
        <Separator className="mb-3" />
        {bottomNavigation.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground",
                sidebarCollapsed && "justify-center px-2",
              )}
            >
              <Icon className="h-[18px] w-[18px] shrink-0" />
              {!sidebarCollapsed && <span>{item.title}</span>}
            </Link>
          );
        })}
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleSidebar}
          className={cn("w-full text-muted-foreground", sidebarCollapsed && "px-2")}
        >
          <ChevronLeft className={cn("h-4 w-4 transition-transform", sidebarCollapsed && "rotate-180")} />
          {!sidebarCollapsed && <span>Collapse</span>}
        </Button>
      </div>
    </aside>
  );
}
