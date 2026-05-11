import { useState } from "react";
import { Activity, Coins, Zap, CheckCircle, PauseCircle, AlertOctagon } from "lucide-react";
import { StatCard } from "./components/StatCard";
import { DecisionChart } from "./components/DecisionChart";
import { DLQTable, DLQBadge } from "./components/DLQTable";
import { useTelemetry } from "./hooks/useTelemetry";

export default function App() {
  const { stats, dlq, loading } = useTelemetry(5000);
  const [dismissing, setDismissing] = useState<Set<number>>(new Set());

  async function handleDismiss(index: number) {
    setDismissing((s) => new Set(s).add(index));
    await fetch(`/api/telemetry/dlq/${index}`, { method: "DELETE" });
    setDismissing((s) => {
      const n = new Set(s);
      n.delete(index);
      return n;
    });
  }

  return (
    <div className="min-h-screen px-6 py-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-600 rounded-xl p-2">
            <Zap size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">OpsPilot</h1>
            <p className="text-xs text-gray-500">AI-powered e-commerce ops agent</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          Live · polling every 5s
        </div>
      </div>

      {loading ? (
        <div className="text-gray-600 text-sm text-center py-20">Loading telemetry…</div>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
            <StatCard
              label="Total Events"
              value={stats?.total_events ?? 0}
              icon={<Activity size={22} />}
              accent="text-indigo-400"
            />
            <StatCard
              label="Released"
              value={stats?.total_release ?? 0}
              icon={<CheckCircle size={22} />}
              accent="text-emerald-400"
            />
            <StatCard
              label="Held"
              value={stats?.total_hold ?? 0}
              icon={<PauseCircle size={22} />}
              accent="text-amber-400"
            />
            <StatCard
              label="Escalated"
              value={stats?.total_escalate ?? 0}
              icon={<AlertOctagon size={22} />}
              accent="text-red-400"
            />
            <StatCard
              label="Total Tokens"
              value={(stats?.total_tokens ?? 0).toLocaleString()}
              icon={<Coins size={22} />}
              accent="text-violet-400"
            />
          </div>

          {/* Middle row: chart + DLQ */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
              <h2 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-widest">
                Decision breakdown
              </h2>
              {stats && <DecisionChart stats={stats} />}
            </div>

            <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
              <h2 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-widest flex items-center gap-2">
                Dead-letter queue <DLQBadge count={dlq.length} />
              </h2>
              <DLQTable
                items={dlq.filter((_, i) => !dismissing.has(i))}
                onDismiss={handleDismiss}
              />
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-gray-700">
            OpsPilot · LangGraph + Claude Sonnet · LangSmith traced
          </p>
        </>
      )}
    </div>
  );
}
