import React from "react";
import { Settings, Trash2 } from "lucide-react";
import Sparkline from "./Sparkline";

function Badge({ kind, children }) {
  const map = {
    golden_cross: "bg-[var(--signal-sell-bg)] text-[var(--signal-sell)] border-[var(--signal-sell)]/20",
    death_cross: "bg-[var(--signal-buy-bg)] text-[var(--signal-buy)] border-[var(--signal-buy)]/20",
    oversold: "bg-[var(--signal-buy-bg)] text-[var(--signal-buy)] border-[var(--signal-buy)]/20",
    overbought: "bg-[var(--signal-sell-bg)] text-[var(--signal-sell)] border-[var(--signal-sell)]/20",
    above: "bg-[var(--signal-sell-bg)] text-[var(--signal-sell)] border-[var(--signal-sell)]/20",
    below: "bg-[var(--signal-buy-bg)] text-[var(--signal-buy)] border-[var(--signal-buy)]/20",
    stoch_oversold: "bg-[var(--signal-buy-bg)] text-[var(--signal-buy)] border-[var(--signal-buy)]/20",
    stoch_overbought: "bg-[var(--signal-sell-bg)] text-[var(--signal-sell)] border-[var(--signal-sell)]/20",
    bb_lower: "bg-[var(--signal-buy-bg)] text-[var(--signal-buy)] border-[var(--signal-buy)]/20",
    bb_upper: "bg-[var(--signal-sell-bg)] text-[var(--signal-sell)] border-[var(--signal-sell)]/20",
    neutral: "bg-gray-100 text-[var(--text-secondary)] border-[var(--border)]",
  };
  return (
    <span className={`px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded-sm border ${map[kind] || map.neutral}`}>
      {children}
    </span>
  );
}

function fmtNum(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export default function TickerRow({ ticker, onDelete, onConfigure }) {
  if (ticker.error) {
    return (
      <div className="border border-[var(--border)] bg-white rounded-sm p-4 flex justify-between items-center" data-testid={`ticker-row-${ticker.symbol}`}>
        <div>
          <div className="font-medium text-sm text-[var(--text-primary)]">{ticker.symbol}</div>
          <div className="text-xs text-[var(--signal-sell)] font-mono">{ticker.error}</div>
        </div>
        <button
          data-testid={`delete-ticker-${ticker.symbol}`}
          onClick={() => onDelete(ticker.symbol)}
          className="p-1.5 text-[var(--text-tertiary)] hover:text-[var(--signal-sell)] hover:bg-gray-50 rounded-sm transition-colors"
        >
          <Trash2 size={14} strokeWidth={1.5} />
        </button>
      </div>
    );
  }

  const change = ticker.last_price - ticker.prev_close;
  const pct = (change / ticker.prev_close) * 100;
  const positive = change >= 0;
  const rsiBadge = ticker.rsi_signal;
  const crossBadge = ticker.crossover;
  const position = ticker.ma_position;
  const maType = (ticker.ma_type || "sma").toUpperCase();
  const stochSig = ticker.stoch_signal;
  const bbSig = ticker.bb_signal;
  const s = ticker.settings || {};

  // Per-ticker enabled flags (hide indicators when no alert toggle is active)
  const showRsi = s.alert_rsi_low || s.alert_rsi_high;
  const showMA = s.alert_golden_cross || s.alert_death_cross;
  const showStoch = s.alert_stoch_low || s.alert_stoch_high;
  const showBB = s.alert_bb_lower || s.alert_bb_upper;

  // Outer border:
  // - GREEN (thick): Stoch oversold + Bollinger lower touch (entry signal)
  // - YELLOW (thick): one of the two
  const stochLow = stochSig === "stoch_oversold" && s.alert_stoch_low;
  const bbLowTouch = bbSig === "bb_lower" && s.alert_bb_lower;
  const greenOutline = stochLow && bbLowTouch;
  const yellowOutline = !greenOutline && (stochLow || bbLowTouch);

  return (
    <div
      data-testid={`ticker-row-${ticker.symbol}`}
      className={`bg-white rounded-sm transition-colors ${
        greenOutline
          ? "border-4 border-[var(--signal-buy)]"
          : yellowOutline
          ? "border-2 border-[var(--signal-buy)]/30 bg-[var(--signal-buy-bg)]/30"
          : "border border-[var(--border)] hover:border-[var(--border-hover)]"
      }`}
    >
      <div className="grid grid-cols-12 gap-3 items-center px-4 py-3">
        {/* Symbol + Name */}
        <div className="col-span-12 md:col-span-3 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-base font-semibold text-[var(--text-primary)] tracking-tight">
              {ticker.symbol}
            </span>
            <span className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
              {ticker.currency}
            </span>
            {greenOutline && (
              <span data-testid={`buy-flag-${ticker.symbol}`} className="px-1.5 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider rounded-sm bg-[var(--signal-buy)] text-white">
                BUY
              </span>
            )}
            {yellowOutline && (
              <span data-testid={`ready-flag-${ticker.symbol}`} className="px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded-sm bg-[var(--signal-buy-bg)] text-[var(--signal-buy)] border border-[var(--signal-buy)]/30">
                ready to buy
              </span>
            )}
          </div>
          <div className="text-xs text-[var(--text-secondary)] truncate">{ticker.name || "—"}</div>
        </div>

        {/* Price */}
        <div className="col-span-6 md:col-span-2">
          <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">Price</div>
          <div className="font-mono text-sm text-[var(--text-primary)]">{fmtNum(ticker.last_price)}</div>
          <div className={`font-mono text-[11px] ${positive ? "text-[var(--signal-buy)]" : "text-[var(--signal-sell)]"}`}>
            {positive ? "+" : ""}{fmtNum(change)} ({positive ? "+" : ""}{fmtNum(pct)}%)
          </div>
        </div>

        {/* Sparkline */}
        <div className="col-span-6 md:col-span-2 flex justify-start md:justify-center">
          <Sparkline data={ticker.spark || []} width={120} height={36} />
        </div>

        {/* RSI */}
        {showRsi && (
        <div className="col-span-6 md:col-span-2">
          <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
            RSI ({ticker.settings.rsi_period})
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="font-mono text-sm text-[var(--text-primary)]">{fmtNum(ticker.rsi)}</span>
            {rsiBadge && <Badge kind={rsiBadge}>{rsiBadge}</Badge>}
          </div>
        </div>
        )}

        {/* MA */}
        {showMA && (
        <div className="col-span-6 md:col-span-2">
          <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
            {maType} {ticker.ma_short_period}/{ticker.ma_long_period}
          </div>
          <div className="font-mono text-[11px] text-[var(--text-secondary)] mt-0.5">
            {fmtNum(ticker.ma_short_value)} / {fmtNum(ticker.ma_long_value)}
          </div>
          <div className="flex flex-wrap gap-1 mt-1">
            {position && (
              <Badge kind={position} data-testid={`ma-position-${ticker.symbol}`}>
                {position === "above" ? "↑ short > long" : position === "below" ? "↓ short < long" : "equal"}
              </Badge>
            )}
            {crossBadge && (
              <Badge kind={crossBadge}>
                {crossBadge === "death_cross" ? "↓ death cross" : crossBadge === "golden_cross" ? "↑ golden cross" : crossBadge.replace("_", " ")}
              </Badge>
            )}
          </div>
        </div>
        )}

        {/* Actions */}
        <div className="col-span-12 md:col-span-1 flex justify-end gap-1">
          <button
            data-testid={`configure-ticker-${ticker.symbol}`}
            onClick={() => onConfigure(ticker)}
            className="p-1.5 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-gray-50 rounded-sm transition-colors"
            title="Configure ticker"
          >
            <Settings size={14} strokeWidth={1.5} />
          </button>
          <button
            data-testid={`delete-ticker-${ticker.symbol}`}
            onClick={() => onDelete(ticker.symbol)}
            className="p-1.5 text-[var(--text-tertiary)] hover:text-[var(--signal-sell)] hover:bg-gray-50 rounded-sm transition-colors"
            title="Remove ticker"
          >
            <Trash2 size={14} strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Secondary row: Stoch RSI + Bollinger */}
      {(showStoch || showBB) && (
      <div className="grid grid-cols-12 gap-3 px-4 pb-3 border-t border-[var(--border)] pt-2">
        {showStoch && (
        <div className="col-span-12 md:col-span-4 md:col-start-4">
          <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
            Stoch RSI ({ticker.settings.stoch_rsi_period}/{ticker.settings.stoch_period}, {ticker.settings.stoch_k_smooth}/{ticker.settings.stoch_d_smooth})
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="font-mono text-xs text-[var(--text-primary)]">
              K {fmtNum(ticker.stoch_k)} / D {fmtNum(ticker.stoch_d)}
            </span>
            {stochSig && <Badge kind={stochSig}>{stochSig.replace("stoch_", "")}</Badge>}
          </div>
        </div>
        )}
        {showBB && (
        <div className="col-span-12 md:col-span-5">
          <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
            Bollinger ({ticker.settings.bb_period}, σ={ticker.settings.bb_std})
          </div>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className="font-mono text-xs text-[var(--text-secondary)]">
              <span className="text-[var(--signal-sell)]">↑{fmtNum(ticker.bb_upper)}</span>
              <span className="mx-1">·</span>
              {fmtNum(ticker.bb_middle)}
              <span className="mx-1">·</span>
              <span className="text-[var(--signal-buy)]">↓{fmtNum(ticker.bb_lower)}</span>
            </span>
            {bbSig && <Badge kind={bbSig}>{bbSig === "bb_lower" ? "touching lower" : "touching upper"}</Badge>}
            {greenOutline && (
              <span data-testid={`combo-badge-${ticker.symbol}`} className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider rounded-sm bg-[var(--signal-buy)] text-white">
                combo
              </span>
            )}
          </div>
        </div>
        )}
      </div>
      )}
    </div>
  );
}
