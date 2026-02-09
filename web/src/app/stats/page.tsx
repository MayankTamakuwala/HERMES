"use client";

import { StatsCards } from "@/components/stats/stats-cards";

export default function StatsPage() {
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-6 text-2xl font-bold">Statistics</h1>
      <StatsCards />
    </div>
  );
}
