"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface SettingItem {
  name: string;
  envVar: string;
  defaultValue: string;
}

const settingGroups: { title: string; items: SettingItem[] }[] = [
  {
    title: "Search",
    items: [
      { name: "Retrieval Mode", envVar: "HERMES_SEARCH_RETRIEVAL_MODE", defaultValue: "hybrid" },
      { name: "Top K Retrieve", envVar: "HERMES_SEARCH_TOP_K_RETRIEVE", defaultValue: "100" },
      { name: "Top K Rerank", envVar: "HERMES_SEARCH_TOP_K_RERANK", defaultValue: "10" },
      { name: "Max Rerank Candidates", envVar: "HERMES_SEARCH_MAX_RERANK_CANDIDATES", defaultValue: "50" },
      { name: "Rerank Timeout (s)", envVar: "HERMES_SEARCH_RERANK_TIMEOUT_SECONDS", defaultValue: "10.0" },
      { name: "RRF K", envVar: "HERMES_SEARCH_RRF_K", defaultValue: "60" },
    ],
  },
  {
    title: "Chunking",
    items: [
      { name: "Max Chars", envVar: "HERMES_CHUNK_MAX_CHARS", defaultValue: "1500" },
      { name: "Overlap Lines", envVar: "HERMES_CHUNK_OVERLAP_LINES", defaultValue: "3" },
      { name: "Min Chars", envVar: "HERMES_CHUNK_MIN_CHARS", defaultValue: "50" },
    ],
  },
  {
    title: "Models",
    items: [
      { name: "Bi-encoder Model", envVar: "HERMES_EMBED_BIENCODER_MODEL", defaultValue: "all-MiniLM-L6-v2" },
      { name: "Bi-encoder Batch Size", envVar: "HERMES_EMBED_BIENCODER_BATCH_SIZE", defaultValue: "64" },
      { name: "Bi-encoder Max Length", envVar: "HERMES_EMBED_BIENCODER_MAX_LENGTH", defaultValue: "512" },
      { name: "Cross-encoder Model", envVar: "HERMES_EMBED_CROSSENCODER_MODEL", defaultValue: "cross-encoder/ms-marco-MiniLM-L-6-v2" },
      { name: "Cross-encoder Batch Size", envVar: "HERMES_EMBED_CROSSENCODER_BATCH_SIZE", defaultValue: "16" },
      { name: "Cross-encoder Max Length", envVar: "HERMES_EMBED_CROSSENCODER_MAX_LENGTH", defaultValue: "512" },
      { name: "Query Cache Size", envVar: "HERMES_EMBED_QUERY_CACHE_SIZE", defaultValue: "1024" },
    ],
  },
  {
    title: "Index",
    items: [
      { name: "Use IVF", envVar: "HERMES_INDEX_FAISS_USE_IVF", defaultValue: "false" },
      { name: "FAISS nprobe", envVar: "HERMES_INDEX_FAISS_NPROBE", defaultValue: "8" },
      { name: "IVF nlist", envVar: "HERMES_INDEX_FAISS_IVF_NLIST", defaultValue: "100" },
    ],
  },
  {
    title: "General",
    items: [
      { name: "Artifacts Directory", envVar: "HERMES_ARTIFACTS_DIR", defaultValue: "artifacts" },
      { name: "Log Level", envVar: "HERMES_LOG_LEVEL", defaultValue: "INFO" },
      { name: "JSON Logging", envVar: "HERMES_LOG_JSON", defaultValue: "false" },
    ],
  },
];

export default function SettingsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings Reference</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configuration is managed via environment variables or a <code className="rounded bg-muted px-1">.env</code> file. Below are all available settings with their defaults.
        </p>
      </div>

      {settingGroups.map((group) => (
        <Card key={group.title}>
          <CardHeader>
            <CardTitle>{group.title}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {group.items.map((item) => (
                <div
                  key={item.envVar}
                  className="flex items-center justify-between py-2.5 text-sm"
                >
                  <div>
                    <p className="font-medium">{item.name}</p>
                    <p className="font-mono text-xs text-muted-foreground">
                      {item.envVar}
                    </p>
                  </div>
                  <code className="rounded bg-muted px-2 py-0.5 text-xs">
                    {item.defaultValue}
                  </code>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
