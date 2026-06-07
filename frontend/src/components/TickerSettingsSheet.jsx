import React, { useState } from "react";
import { X } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";

function Field({ label, children, hint }) {
  return (
    <div>
      <label className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-tertiary)] block mb-1.5">
        {label}
      </label>
      {children}
      {hint && <div className="text-[10px] text-[var(--text-tertiary)] font-mono mt-1">{hint}</div>}
    </div>
  );
}

function NumInput({ value, onChange, step = 1, testid, placeholder }) {
  return (
    <input
      data-testid={testid}
      type="number"
      step={step}
      value={value === null || value === undefined ? "" : value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      className="w-full border border-[var(--border)] bg-white rounded-sm px-3 py-2 text-sm font-mono text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)]"
    />
  );
}

function SwitchRow({ label, checked, onChange, testid }) {
  return (
    <label className="flex items-center justify-between py-2 cursor-pointer">
      <span className="text-sm text-[var(--text-primary)]">{label}</span>
      <button
        data-testid={testid}
        type="button"
        role="switch"
        aria-checked={!!checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 items-center rounded-sm border transition-colors ${
          checked ? "bg-[var(--brand)] border-[var(--brand)]" : "bg-gray-100 border-[var(--border)]"
        }`}
      >
        <span className={`inline-block h-3.5 w-3.5 bg-white shadow-sm transition-transform ${checked ? "translate-x-4" : "translate-x-0.5"}`} />
      </button>
    </label>
  );
}

function TriToggle({ label, value, onChange, testid }) {
  // value: true | false | null (= inherit global)
  const opts = [
    { v: null, label: "Inherit" },
    { v: true, label: "On" },
    { v: false, label: "Off" },
  ];
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-[var(--text-primary)]">{label}</span>
      <div className="inline-flex border border-[var(--border)] rounded-sm overflow-hidden" data-testid={testid}>
        {opts.map((o) => (
          <button
            key={String(o.v)}
            type="button"
            onClick={() => onChange(o.v)}
            className={`px-2 py-1 text-[10px] uppercase tracking-wider font-mono ${
              value === o.v
                ? "bg-[var(--brand)] text-white"
                : "bg-white text-[var(--text-secondary)] hover:bg-gray-50"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function TickerSettingsSheet({ ticker, onClose, onSaved, globalSettings }) {
  const [overrides, setOverrides] = useState(ticker?.overrides || {});
  const [saving, setSaving] = useState(false);

  if (!ticker) return null;

  const set = (k, v) => setOverrides((o) => ({ ...o, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      // Strip empty strings; keep nulls (inherit)
      const cleaned = Object.fromEntries(
        Object.entries(overrides).map(([k, v]) => [k, v === "" ? null : v])
      );
      await api.updateOverrides(ticker.symbol, cleaned);
      toast.success(`${ticker.symbol} settings saved`);
      onSaved?.();
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const g = globalSettings || {};

  return (
    <div className="fixed inset-0 z-50 flex" data-testid="ticker-settings-panel">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative ml-auto w-full max-w-md h-full bg-white border-l border-[var(--border)] shadow-lg overflow-y-auto scrollbar-thin">
        <div className="sticky top-0 bg-white border-b border-[var(--border)] px-5 py-4 flex justify-between items-center">
          <div>
            <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
              Per-Ticker Override
            </div>
            <h2 className="text-lg font-medium text-[var(--text-primary)] font-mono">{ticker.symbol}</h2>
          </div>
          <button
            data-testid="close-ticker-settings-btn"
            onClick={onClose}
            className="p-1.5 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-gray-50 rounded-sm transition-colors"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>

        <div className="px-5 py-6 space-y-8">
          <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
            Leave fields empty to inherit global values. Toggle alerts to <span className="font-mono">Inherit</span> to use global config.
          </p>

          <section>
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3 border-b border-[var(--border)] pb-2">RSI</h3>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Period" hint={`global: ${g.rsi_period ?? "—"}`}>
                <NumInput testid="t-rsi-period" value={overrides.rsi_period ?? null} onChange={(v) => set("rsi_period", v)} placeholder="—" />
              </Field>
              <Field label="Lower" hint={`global: ${g.rsi_lower ?? "—"}`}>
                <NumInput testid="t-rsi-lower" value={overrides.rsi_lower ?? null} onChange={(v) => set("rsi_lower", v)} step={0.5} placeholder="—" />
              </Field>
              <Field label="Upper" hint={`global: ${g.rsi_upper ?? "—"}`}>
                <NumInput testid="t-rsi-upper" value={overrides.rsi_upper ?? null} onChange={(v) => set("rsi_upper", v)} step={0.5} placeholder="—" />
              </Field>
            </div>
          </section>

          <section>
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3 border-b border-[var(--border)] pb-2">Moving Averages</h3>
            <Field label="Type" hint={`global: ${(g.ma_type || "sma").toUpperCase()}`}>
              <div className="inline-flex border border-[var(--border)] rounded-sm overflow-hidden" data-testid="t-ma-type">
                {[
                  { v: null, label: "Inherit" },
                  { v: "sma", label: "SMA" },
                  { v: "ema", label: "EMA" },
                ].map((o) => (
                  <button
                    key={String(o.v)}
                    type="button"
                    onClick={() => set("ma_type", o.v)}
                    className={`px-2 py-1 text-[10px] uppercase tracking-wider font-mono ${
                      (overrides.ma_type ?? null) === o.v
                        ? "bg-[var(--brand)] text-white"
                        : "bg-white text-[var(--text-secondary)] hover:bg-gray-50"
                    }`}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </Field>
            <div className="grid grid-cols-2 gap-3 mt-3">
              <Field label="Short" hint={`global: ${g.ma_short ?? "—"}`}>
                <NumInput testid="t-ma-short" value={overrides.ma_short ?? null} onChange={(v) => set("ma_short", v)} placeholder="—" />
              </Field>
              <Field label="Long" hint={`global: ${g.ma_long ?? "—"}`}>
                <NumInput testid="t-ma-long" value={overrides.ma_long ?? null} onChange={(v) => set("ma_long", v)} placeholder="—" />
              </Field>
            </div>
          </section>

          <section>
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-1 border-b border-[var(--border)] pb-2">Alert Conditions</h3>
            <SwitchRow testid="t-alert-rsi-low" label="RSI Low (oversold)" checked={(overrides.alert_rsi_low ?? g.alert_rsi_low) === true} onChange={(v) => set("alert_rsi_low", v)} />
            <SwitchRow testid="t-alert-rsi-high" label="RSI High (overbought)" checked={(overrides.alert_rsi_high ?? g.alert_rsi_high) === true} onChange={(v) => set("alert_rsi_high", v)} />
            <SwitchRow testid="t-alert-golden" label="Golden Cross (short crosses ABOVE long)" checked={(overrides.alert_golden_cross ?? g.alert_golden_cross) === true} onChange={(v) => set("alert_golden_cross", v)} />
            <SwitchRow testid="t-alert-death" label="Death Cross (short crosses BELOW long)" checked={(overrides.alert_death_cross ?? g.alert_death_cross) === true} onChange={(v) => set("alert_death_cross", v)} />
            <SwitchRow testid="t-alert-stoch-low" label="Stoch RSI Low (oversold)" checked={(overrides.alert_stoch_low ?? g.alert_stoch_low) === true} onChange={(v) => set("alert_stoch_low", v)} />
            <SwitchRow testid="t-alert-stoch-high" label="Stoch RSI High (overbought)" checked={(overrides.alert_stoch_high ?? g.alert_stoch_high) === true} onChange={(v) => set("alert_stoch_high", v)} />
            <SwitchRow testid="t-alert-bb-lower" label="Price touching lower Bollinger" checked={(overrides.alert_bb_lower ?? g.alert_bb_lower) === true} onChange={(v) => set("alert_bb_lower", v)} />
            <SwitchRow testid="t-alert-bb-upper" label="Price touching upper Bollinger" checked={(overrides.alert_bb_upper ?? g.alert_bb_upper) === true} onChange={(v) => set("alert_bb_upper", v)} />
          </section>
        </div>

        <div className="sticky bottom-0 bg-white border-t border-[var(--border)] px-5 py-3 flex justify-start gap-2">
          <button
            data-testid="save-ticker-settings-btn"
            onClick={save}
            disabled={saving}
            className="bg-[var(--brand)] hover:bg-[var(--brand-hover)] text-white px-4 py-2 rounded-sm text-sm font-medium transition-colors disabled:opacity-60"
          >
            {saving ? "Saving..." : "Save"}
          </button>
          <button
            onClick={onClose}
            className="border border-[var(--border)] hover:bg-gray-50 text-[var(--text-primary)] px-4 py-2 rounded-sm text-sm font-medium transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
