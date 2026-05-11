import { useState, useEffect } from "react";

export interface Stats {
  total_events: number;
  total_hold: number;
  total_release: number;
  total_escalate: number;
  total_tokens: number;
}

export interface DLQItem {
  event_type: string;
  order_id: string;
  error: string;
  ts: number;
}

export function useTelemetry(pollMs = 5000) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [dlq, setDlq] = useState<DLQItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAll() {
      try {
        const [statsRes, dlqRes] = await Promise.all([
          fetch("/api/telemetry/stats"),
          fetch("/api/telemetry/dlq"),
        ]);
        if (statsRes.ok) setStats(await statsRes.json());
        if (dlqRes.ok) {
          const data = await dlqRes.json();
          setDlq(data.items ?? []);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchAll();
    const id = setInterval(fetchAll, pollMs);
    return () => clearInterval(id);
  }, [pollMs]);

  return { stats, dlq, loading };
}
