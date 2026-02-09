"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SearchResultItem } from "@/lib/api";

interface ResultCardProps {
  result: SearchResultItem;
}

export function ResultCard({ result }: ResultCardProps) {
  const rankChanged = result.retrieval_rank !== result.final_rank;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-medium">
              {result.file_path}
            </span>
            <span className="text-xs text-muted-foreground">
              L{result.start_line}-{result.end_line}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            {result.symbol_name && (
              <Badge variant="secondary">{result.symbol_name}</Badge>
            )}
            <Badge variant="outline">{result.language}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {result.code_snippet && (
          <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
            <code className={`language-${result.language}`}>
              {result.code_snippet}
            </code>
          </pre>
        )}

        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span>
            Retrieval: <strong className="text-foreground">{result.retrieval_score.toFixed(4)}</strong>
          </span>
          {result.rerank_score !== null && (
            <span>
              Rerank: <strong className="text-foreground">{result.rerank_score.toFixed(4)}</strong>
            </span>
          )}
          <span>
            Rank: <strong className="text-foreground">#{result.final_rank}</strong>
          </span>
          {rankChanged && (
            <span className="text-xs">
              (was #{result.retrieval_rank})
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
