"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";

export function Header() {
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      try {
        await api.health();
        if (mounted) setConnected(true);
      } catch {
        if (mounted) setConnected(false);
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card px-6">
      <h2 className="text-sm font-medium text-muted-foreground">
        Code Search Engine
      </h2>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Server:</span>
        {connected === null ? (
          <Badge variant="outline">Checking...</Badge>
        ) : connected ? (
          <Badge className="bg-green-600 text-white hover:bg-green-700">Connected</Badge>
        ) : (
          <Badge variant="destructive">Disconnected</Badge>
        )}
      </div>
    </header>
  );
}
