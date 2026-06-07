import React from "react";
import { Activity, RefreshCw } from "lucide-react";

function formatTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toISOString().replace("T", " ").slice(0, 16) + " UTC";
  } catch {
    return iso;
  }
}

export default function StatusBar({ status, onRun, running }) {
  return (
    <div
      data-testid="status-bar"
      className="border border-[var(--border)] bg-white rounded-sm px-4 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
    >
      <div className="flex items-center gap-6 flex-wrap">
        <div className="flex items-center gap-2">
          <Activity size={14} strokeWidth={1.5} className="text-[var(--text-tertiary)]" />
          <span className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
            Last Scan
          </span>
          <span className="font-mono text-xs text-[var(--text-primary)]" data-testid="status-last-run">
            {formatTime(status?.last_run)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
            Next Run
          </span>
          <span className="font-mono text-xs text-[var(--text-primary)]" data-testid="status-next-run">
            {formatTime(status?.next_run)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
            Assets
          </span>
          <span className="font-mono text-xs text-[var(--text-primary)]">
            {status?.tickers_scanned ?? 0}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
            Triggered
          </span>
          <span className="font-mono text-xs text-[var(--text-primary)]">
            {status?.alerts_triggered ?? 0}
          </span>
        </div>
      </div>
      <button
        data-testid="run-scan-btn"
        onClick={onRun}
        disabled={running}
        className="inline-flex items-center gap-2 bg-[var(--brand)] hover:bg-[var(--brand-hover)] text-white px-3 py-1.5 rounded-sm text-xs font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        <RefreshCw size={12} strokeWidth={1.5} className={running ? "animate-spin" : ""} />
        {running ? "Scanning..." : "Run Scan Now"}
      </button>
    </div>
  );
}
