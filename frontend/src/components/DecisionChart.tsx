import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { Stats } from "../hooks/useTelemetry";

const COLORS = {
  Release: "#22c55e",
  Hold: "#f59e0b",
  Escalate: "#ef4444",
};

export function DecisionChart({ stats }: { stats: Stats }) {
  const data = [
    { name: "Release", value: stats.total_release },
    { name: "Hold", value: stats.total_hold },
    { name: "Escalate", value: stats.total_escalate },
  ].filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-600 text-sm">
        No decisions yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={COLORS[entry.name as keyof typeof COLORS]}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
          labelStyle={{ color: "#f9fafb" }}
        />
        <Legend
          iconType="circle"
          formatter={(value) => (
            <span className="text-gray-300 text-sm">{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
