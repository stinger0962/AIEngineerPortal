"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const chartData = [
  { label: "Week 1", learning: 8, practice: 2 },
  { label: "Week 2", learning: 12, practice: 4 },
  { label: "Week 3", learning: 18, practice: 6 },
  { label: "Week 4", learning: 24, practice: 9 },
];

export function ProgressChart() {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="learningFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f77f00" stopOpacity={0.65} />
              <stop offset="95%" stopColor="#f77f00" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="practiceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#264653" stopOpacity={0.45} />
              <stop offset="95%" stopColor="#264653" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <XAxis dataKey="label" stroke="#6b7280" />
          <YAxis stroke="#6b7280" />
          <Tooltip />
          <Area type="monotone" dataKey="learning" stroke="#f77f00" fill="url(#learningFill)" />
          <Area type="monotone" dataKey="practice" stroke="#264653" fill="url(#practiceFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
