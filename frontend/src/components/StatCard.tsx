import type { ReactNode } from "react";

interface Props {
  label: string;
  value: number | string;
  icon: ReactNode;
  accent?: string;
}

export function StatCard({ label, value, icon, accent = "text-indigo-400" }: Props) {
  return (
    <div className="bg-gray-900 rounded-2xl p-5 flex items-center gap-4 border border-gray-800">
      <div className={`text-3xl ${accent}`}>{icon}</div>
      <div>
        <p className="text-xs uppercase tracking-widest text-gray-500">{label}</p>
        <p className="text-2xl font-bold mt-0.5">{value}</p>
      </div>
    </div>
  );
}
