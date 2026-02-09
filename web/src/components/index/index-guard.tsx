"use client";

import { useCallback, useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { WelcomeScreen } from "@/components/index/welcome-screen";
import { api } from "@/lib/api";

interface IndexGuardProps {
  children: React.ReactNode;
}

export function IndexGuard({ children }: IndexGuardProps) {
  const [hasIndex, setHasIndex] = useState<boolean | null>(null);

  const checkIndex = useCallback(async () => {
    try {
      const res = await api.indexCheck();
      setHasIndex(res.has_index);
    } catch {
      // API not reachable yet — treat as no index
      setHasIndex(false);
    }
  }, []);

  useEffect(() => {
    checkIndex();
  }, [checkIndex]);

  // Still loading
  if (hasIndex === null) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Connecting to HERMES...</p>
      </div>
    );
  }

  // No index — show welcome screen
  if (!hasIndex) {
    return <WelcomeScreen onIndexReady={checkIndex} />;
  }

  // Index exists — render normal layout
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
