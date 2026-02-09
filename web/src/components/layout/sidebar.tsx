"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Search", icon: "S" },
  { href: "/index-repo", label: "Index", icon: "I" },
  { href: "/stats", label: "Stats", icon: "A" },
  { href: "/settings", label: "Settings", icon: "G" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-4">
        <Link href="/" className="text-lg font-bold tracking-tight">
          HERMES
        </Link>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {navItems.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <span className="flex h-6 w-6 items-center justify-center rounded bg-muted text-xs font-bold text-muted-foreground">
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t p-4 text-xs text-muted-foreground">
        Hybrid Embedding Retrieval
      </div>
    </aside>
  );
}
