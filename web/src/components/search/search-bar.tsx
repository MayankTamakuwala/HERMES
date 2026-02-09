"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface SearchBarProps {
  onSearch: (query: string) => void;
  loading?: boolean;
}

export function SearchBar({ onSearch, loading }: SearchBarProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) onSearch(query.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        placeholder="Search code..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="flex-1"
      />
      <Button type="submit" disabled={loading || !query.trim()}>
        {loading ? "Searching..." : "Search"}
      </Button>
    </form>
  );
}
