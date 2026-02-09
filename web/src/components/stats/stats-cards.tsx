"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { api, type StatsResponse } from "@/lib/api";

export function StatsCards() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [error, setError] = useState("");
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchStats = async () => {
    try {
      setStats(await api.stats());
      setError("");
    } catch (err) {
      setError(String(err));
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  if (error) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-sm text-destructive">
          {error}
        </CardContent>
      </Card>
    );
  }

  if (!stats) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-sm text-muted-foreground">
          Loading stats...
        </CardContent>
      </Card>
    );
  }

  const items = [
    { label: "Index Size", value: stats.index_size.toLocaleString() },
    { label: "Chunks", value: stats.n_chunks.toLocaleString() },
    { label: "Cache Hit Rate", value: `${(stats.cache_hit_rate * 100).toFixed(1)}%` },
    { label: "Cache Hits", value: stats.cache_hits.toLocaleString() },
    { label: "Cache Misses", value: stats.cache_misses.toLocaleString() },
    { label: "Retrieval Mode", value: stats.retrieval_mode },
    { label: "Bi-encoder", value: stats.biencoder_model },
    { label: "Cross-encoder", value: stats.crossencoder_model },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Switch
          id="auto-refresh"
          checked={autoRefresh}
          onCheckedChange={setAutoRefresh}
        />
        <Label htmlFor="auto-refresh">Auto-refresh (5s)</Label>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <Card key={item.label}>
            <CardHeader className="pb-1">
              <CardTitle className="text-xs font-medium text-muted-foreground">
                {item.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-lg font-bold">{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
