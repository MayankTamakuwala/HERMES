"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, type IndexStatusResponse } from "@/lib/api";

interface WelcomeScreenProps {
  onIndexReady: () => void;
}

export function WelcomeScreen({ onIndexReady }: WelcomeScreenProps) {
  const [repoPath, setRepoPath] = useState("");
  const [status, setStatus] = useState<IndexStatusResponse>({ state: "idle" });
  const [message, setMessage] = useState("");

  const fetchStatus = async () => {
    try {
      const s = await api.indexStatus();
      setStatus(s);
    } catch {
      /* ignore */
    }
  };

  // Poll while indexing
  useEffect(() => {
    if (status.state !== "indexing") return;
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [status.state]);

  // Transition to main UI when indexing completes
  useEffect(() => {
    if (status.state === "done") {
      const timer = setTimeout(onIndexReady, 1500);
      return () => clearTimeout(timer);
    }
  }, [status.state, onIndexReady]);

  const handleIndex = async () => {
    if (!repoPath.trim()) return;
    setMessage("");
    try {
      const res = await api.startIndexing(repoPath.trim());
      setMessage(res.message);
      fetchStatus();
    } catch (err) {
      setMessage(String(err));
    }
  };

  const stateColor: Record<string, string> = {
    idle: "outline",
    indexing: "default",
    done: "secondary",
    error: "destructive",
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-lg space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">HERMES</h1>
          <p className="text-muted-foreground">
            Hybrid Embedding Retrieval with Multi-stage Evaluation &amp; Scoring
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Get Started</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              No index found. Index a repository to enable code search.
            </p>
            <div className="space-y-1.5">
              <Label>Local Repository Path</Label>
              <Input
                placeholder="/path/to/your/repo"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleIndex()}
                disabled={status.state === "indexing"}
              />
            </div>
            <Button
              onClick={handleIndex}
              disabled={!repoPath.trim() || status.state === "indexing"}
              className="w-full"
            >
              {status.state === "indexing" ? "Indexing..." : "Start Indexing"}
            </Button>
            {message && (
              <p className="text-sm text-muted-foreground">{message}</p>
            )}
          </CardContent>
        </Card>

        {status.state !== "idle" && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Status
                <Badge
                  variant={
                    stateColor[status.state] as
                      | "outline"
                      | "default"
                      | "secondary"
                      | "destructive"
                  }
                >
                  {status.state}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {status.state === "indexing" && (
                <p className="text-sm text-muted-foreground">
                  Indexing <strong>{status.repo_path}</strong>...
                </p>
              )}
              {status.state === "done" && status.summary && (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {Object.entries(status.summary).map(([k, v]) => (
                      <div key={k}>
                        <span className="text-muted-foreground">{k}: </span>
                        <strong>{String(v)}</strong>
                      </div>
                    ))}
                  </div>
                  <p className="text-sm text-green-600 dark:text-green-400">
                    Index ready! Loading search...
                  </p>
                </div>
              )}
              {status.state === "error" && (
                <p className="text-sm text-destructive">{status.message}</p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
