"use client";

import { useEffect, useState } from "react";
import { ChartView } from "./chart-view";
import { OracleProbe } from "./oracle-probe"; // Task 4 替换为 ChatDock
import { TermCard, type TermInfo } from "./term-card";
import { hasChart, type ZiweiProfileOut } from "@/lib/ziwei/api";

export function ZiweiWorkspace({ profile }: { profile: ZiweiProfileOut }) {
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);
  const [term, setTerm] = useState<TermInfo | null>(null);

  // 档案切换时回到总览、清术语卡
  useEffect(() => {
    setSelectedBranch(null);
    setTerm(null);
  }, [profile.id]);

  if (!hasChart(profile)) return null;
  const chart = profile.chart_json;

  return (
    <div className="relative">
      <ChartView chart={chart} selectedBranch={selectedBranch} onSelectBranch={setSelectedBranch} />
      {term ? <TermCard info={term} onClose={() => setTerm(null)} /> : null}
      <OracleProbe profileId={profile.id} />
    </div>
  );
}
