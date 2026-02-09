"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, type IndexStatusResponse, type StatsResponse } from "@/lib/api";

export function IndexPanel() {
  const [repoPath, setRepoPath] = useState("");
  const [status, setStatus] = useState<IndexStatusResponse>({ state: "idle" });
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [message, setMessage] = useState("");

  const fetchStatus = async () => {
    try {
      const s = await api.indexStatus();
      setStatus(s);
    } catch {
      /* ignore */
    }
  };

  const fetchStats = async () => {
    try {
      setStats(await api.stats());
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchStats();
  }, []);

  // Poll while indexing
  useEffect(() => {
    if (status.state !== "indexing") return;
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [status.state]);

  // Refresh stats after indexing completes
  useEffect(() => {
    if (status.state === "done") fetchStats();
  }, [status.state]);

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

  const handleReload = async () => {
    setMessage("");
    try {
      const res = await api.reloadIndex();
      setMessage(`Reloaded — ${res.n_chunks} chunks`);
      fetchStats();
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
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Index a Repository</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>Local Repository Path</Label>
            <Input
              placeholder="/path/to/your/repo"
              value={repoPath}
              onChange={(e) => setRepoPath(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleIndex}
              disabled={!repoPath.trim() || status.state === "indexing"}
            >
              {status.state === "indexing" ? "Indexing..." : "Start Indexing"}
            </Button>
            <Button variant="outline" onClick={handleReload}>
              Reload Index
            </Button>
          </div>
          {message && (
            <p className="text-sm text-muted-foreground">{message}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Status
            <Badge variant={stateColor[status.state] as "outline" | "default" | "secondary" | "destructive"}>
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
            <div className="grid grid-cols-2 gap-2 text-sm">
              {Object.entries(status.summary).map(([k, v]) => (
                <div key={k}>
                  <span className="text-muted-foreground">{k}: </span>
                  <strong>{String(v)}</strong>
                </div>
              ))}
            </div>
          )}
          {status.state === "error" && (
            <p className="text-sm text-destructive">{status.message}</p>
          )}
        </CardContent>
      </Card>

      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>Current Index</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">Chunks: </span>
              <strong>{stats.n_chunks.toLocaleString()}</strong>
            </div>
            <div>
              <span className="text-muted-foreground">Index size: </span>
              <strong>{stats.index_size.toLocaleString()}</strong>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
