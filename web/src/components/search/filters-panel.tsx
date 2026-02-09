"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export interface SearchFilters {
  retrieval_mode: "dense" | "sparse" | "hybrid";
  top_k_retrieve: number;
  top_k_rerank: number;
  filter_language: string;
  filter_path_prefix: string;
  return_snippets: boolean;
}

const defaultFilters: SearchFilters = {
  retrieval_mode: "hybrid",
  top_k_retrieve: 100,
  top_k_rerank: 10,
  filter_language: "",
  filter_path_prefix: "",
  return_snippets: true,
};

const languages = [
  "", "python", "javascript", "typescript", "java", "go", "rust",
  "c", "cpp", "csharp", "ruby", "php", "swift", "kotlin", "scala",
];

interface FiltersPanelProps {
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
}

export function FiltersPanel({ filters, onChange }: FiltersPanelProps) {
  const [open, setOpen] = useState(false);

  const update = (partial: Partial<SearchFilters>) =>
    onChange({ ...filters, ...partial });

  return (
    <div className="rounded-md border">
      <Button
        variant="ghost"
        className="w-full justify-between px-4 py-2"
        onClick={() => setOpen(!open)}
      >
        <span className="text-sm font-medium">Filters</span>
        <span className="text-xs text-muted-foreground">{open ? "Hide" : "Show"}</span>
      </Button>
      {open && (
        <div className="grid grid-cols-2 gap-4 border-t p-4 md:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Retrieval Mode</Label>
            <Select
              value={filters.retrieval_mode}
              onValueChange={(v) =>
                update({ retrieval_mode: v as SearchFilters["retrieval_mode"] })
              }
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="dense">Dense</SelectItem>
                <SelectItem value="sparse">Sparse</SelectItem>
                <SelectItem value="hybrid">Hybrid</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Top K Retrieve</Label>
            <Input
              type="number"
              min={1}
              max={1000}
              value={filters.top_k_retrieve}
              onChange={(e) =>
                update({ top_k_retrieve: parseInt(e.target.value) || 100 })
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label>Top K Rerank</Label>
            <Input
              type="number"
              min={1}
              max={200}
              value={filters.top_k_rerank}
              onChange={(e) =>
                update({ top_k_rerank: parseInt(e.target.value) || 10 })
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label>Language</Label>
            <Select
              value={filters.filter_language}
              onValueChange={(v) => update({ filter_language: v })}
            >
              <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
              <SelectContent>
                {languages.map((lang) => (
                  <SelectItem key={lang || "__all"} value={lang || "all"}>
                    {lang || "All"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Path Prefix</Label>
            <Input
              placeholder="e.g. src/"
              value={filters.filter_path_prefix}
              onChange={(e) => update({ filter_path_prefix: e.target.value })}
            />
          </div>

          <div className="flex items-end gap-2 pb-1">
            <Switch
              id="snippets"
              checked={filters.return_snippets}
              onCheckedChange={(v) => update({ return_snippets: v })}
            />
            <Label htmlFor="snippets">Return Snippets</Label>
          </div>
        </div>
      )}
    </div>
  );
}

export { defaultFilters };
