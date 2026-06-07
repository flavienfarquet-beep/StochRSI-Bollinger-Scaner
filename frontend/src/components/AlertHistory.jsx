import React from "react";

function timeAgo(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const sec = Math.floor((Date.now() - d.getTime()) / 1000);
    if (sec < 60) return `${sec}s ago`;
    if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
    return `${Math.floor(sec / 86400)}d ago`;
  } catch {
    return iso;
  }
}

const DOT_COLOR = {
  oversold: "#059669",
  golden_cross: "#059669",
  overbought: "#DC2626",
  death_cross: "#DC2626",
  stoch_oversold: "#059669",
  stoch_overbought: "#DC2626",
  bb_lower_touch: "#059669",
  bb_upper_touch: "#DC2626",
  combo_bullish: "#D97706",
  combo_bearish: "#D97706",
};

export default function AlertHistory({ alerts, onClear }) {
  return (
    <div className="border border-[var(--border)] bg-white rounded-sm overflow-hidden" data-testid="alert-history">
      <div className="border-b border-[var(--border)] px-4 py-3 flex justify-between items-center bg-gray-50/50">
        <h2 className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-tertiary)]">
          Alert History
        </h2>
        {alerts.length > 0 && (
          <button
            data-testid="clear-alerts-btn"
            onClick={onClear}
            className="text-[10px] uppercase tracking-wider text-[var(--text-tertiary)] hover:text-[var(--signal-sell)] transition-colors"
          >
            Clear
          </button>
        )}
      </div>
      <div className="max-h-[420px] overflow-y-auto scrollbar-thin">
        {alerts.length === 0 ? (
          <div className="p-6 text-center text-xs text-[var(--text-tertiary)] font-mono">
            No alerts triggered yet.
          </div>
        ) : (
          <ul>
            {alerts.map((a) => (
              <li
                key={a.id}
                data-testid={`alert-${a.id}`}
                className="px-4 py-3 border-b border-[var(--border)] last:border-b-0 flex items-start gap-3"
              >
                <span
                  className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  style={{ background: DOT_COLOR[a.type] || "#9CA3AF" }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between gap-2 items-baseline">
                    <span className="font-mono text-sm font-semibold text-[var(--text-primary)]">
                      {a.symbol}
                    </span>
                    <span className="font-mono text-[10px] text-[var(--text-tertiary)] shrink-0">
                      {timeAgo(a.triggered_at)}
                    </span>
                  </div>
                  <div className="text-xs text-[var(--text-secondary)] mt-0.5">
                    {a.type.replace("_", " ").toUpperCase()}
                    {a.value != null && (
                      <span className="font-mono ml-2 text-[var(--text-tertiary)]">
                        RSI {a.value.toFixed(2)}
                      </span>
                    )}
                    {a.price != null && (
                      <span className="font-mono ml-2 text-[var(--text-tertiary)]">
                        @ {a.price.toFixed(2)}
                      </span>
                    )}
                  </div>
                  {a.email_sent && (
                    <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--signal-buy)] mt-0.5">
                      email sent
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
