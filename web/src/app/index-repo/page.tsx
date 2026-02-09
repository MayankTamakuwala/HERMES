"use client";

import { IndexPanel } from "@/components/index/index-panel";

export default function IndexPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">Index Management</h1>
      <IndexPanel />
    </div>
  );
}
