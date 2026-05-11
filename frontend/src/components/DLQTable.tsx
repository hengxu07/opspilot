import { AlertTriangle, Trash2 } from "lucide-react";
import type { DLQItem } from "../hooks/useTelemetry";

interface Props {
  items: DLQItem[];
  onDismiss: (index: number) => void;
}

export function DLQTable({ items, onDismiss }: Props) {
  if (items.length === 0) {
    return (
      <p className="text-gray-600 text-sm text-center py-8">Dead-letter queue is empty</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 text-xs uppercase tracking-widest border-b border-gray-800">
            <th className="pb-2 text-left">Order</th>
            <th className="pb-2 text-left">Event</th>
            <th className="pb-2 text-left">Error</th>
            <th className="pb-2 text-left">Time</th>
            <th className="pb-2" />
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition">
              <td className="py-3 pr-4 font-mono text-orange-400">{item.order_id}</td>
              <td className="py-3 pr-4 text-gray-400">{item.event_type}</td>
              <td className="py-3 pr-4 text-red-400 max-w-xs truncate">{item.error}</td>
              <td className="py-3 pr-4 text-gray-500 whitespace-nowrap">
                {new Date(item.ts * 1000).toLocaleString()}
              </td>
              <td className="py-3">
                <button
                  onClick={() => onDismiss(i)}
                  className="text-gray-600 hover:text-red-400 transition"
                  title="Dismiss"
                >
                  <Trash2 size={15} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DLQBadge({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span className="inline-flex items-center gap-1 bg-red-900/50 text-red-400 text-xs font-semibold px-2 py-0.5 rounded-full">
      <AlertTriangle size={11} /> {count}
    </span>
  );
}
