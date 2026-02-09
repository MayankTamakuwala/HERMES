"use client";

import { useState } from "react";
import { SearchBar } from "@/components/search/search-bar";
import { FiltersPanel, defaultFilters, type SearchFilters } from "@/components/search/filters-panel";
import { ResultCard } from "@/components/search/result-card";
import { TimingBar } from "@/components/search/timing-bar";
import { Badge } from "@/components/ui/badge";
import { api, type SearchResponse } from "@/lib/api";

export default function SearchPage() {
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (query: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await api.search({
        query,
        top_k_retrieve: filters.top_k_retrieve,
        top_k_rerank: filters.top_k_rerank,
        retrieval_mode: filters.retrieval_mode,
        filter_language: filters.filter_language && filters.filter_language !== "all"
          ? filters.filter_language
          : null,
        filter_path_prefix: filters.filter_path_prefix || null,
        return_snippets: filters.return_snippets,
      });
      setResponse(res);
    } catch (err) {
      setError(String(err));
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <SearchBar onSearch={handleSearch} loading={loading} />
      <FiltersPanel filters={filters} onChange={setFilters} />

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {response && (
        <>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span>{response.results.length} results</span>
            <Badge variant="outline">{response.retrieval_mode}</Badge>
            <span>Candidates: {response.total_candidates}</span>
            {response.rerank_skipped && (
              <Badge variant="secondary">Rerank skipped</Badge>
            )}
            <span className="ml-auto font-mono">{response.request_id}</span>
          </div>

          <TimingBar timings={response.timings_ms} />

          <div className="space-y-3">
            {response.results.map((r) => (
              <ResultCard key={r.chunk_id} result={r} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
