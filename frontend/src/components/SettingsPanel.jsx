import React, { useEffect, useState } from "react";
import { X, Send, Bell, BellOff } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";

function Field({ label, children }) {
  return (
    <div>
      <label className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-tertiary)] block mb-1.5">
        {label}
      </label>
      {children}
    </div>
  );
}

function NumInput({ value, onChange, step = 1, min, max, testid }) {
  return (
    <input
      data-testid={testid}
      type="number"
      step={step}
      min={min}
      max={max}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
      className="w-full border border-[var(--border)] bg-white rounded-sm px-3 py-2 text-sm font-mono text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)]"
    />
  );
}

function ToggleRow({ label, checked, onChange, testid }) {
  return (
    <label className="flex items-center justify-between py-2 cursor-pointer">
      <span className="text-sm text-[var(--text-primary)]">{label}</span>
      <button
        data-testid={testid}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 items-center rounded-sm border transition-colors ${
          checked ? "bg-[var(--brand)] border-[var(--brand)]" : "bg-gray-100 border-[var(--border)]"
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 bg-white shadow-sm transition-transform ${
            checked ? "translate-x-4" : "translate-x-0.5"
          }`}
        />
      </button>
    </label>
  );
}

export default function SettingsPanel({ open, onClose, onSaved }) {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [pushEnabled, setPushEnabled] = useState(() =>
    typeof Notification !== "undefined" && Notification.permission === "granted"
  );

  useEffect(() => {
    if (open) {
      api.getSettings().then((s) => setSettings(s));
    }
  }, [open]);

  if (!open) return null;

  const handleChange = (k, v) => setSettings((s) => ({ ...s, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      await api.updateSettings(settings);
      toast.success("Settings saved");
      onSaved?.();
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const enablePush = async () => {
    if (!("Notification" in window)) {
      toast.error("Notifications not supported in this browser");
      return;
    }
    if (!window.isSecureContext) {
      toast.error("Push requires HTTPS (secure context)");
      return;
    }
    let perm = Notification.permission;
    if (perm === "default") {
      perm = await Notification.requestPermission();
    }
    if (perm === "granted") {
      setPushEnabled(true);
      handleChange("push_enabled", true);
      try {
        new Notification("RSI & MA Tracker", { body: "Push notifications enabled." });
      } catch (e) {
        // Some browsers block direct Notification(); fall back to toast only
      }
      toast.success("Push notifications enabled");
    } else if (perm === "denied") {
      toast.error("Permission denied. Enable notifications in your browser settings.");
    } else {
      toast.error("Permission not granted");
    }
  };

  const testPush = () => {
    if (typeof Notification === "undefined") {
      toast.error("Notifications not supported");
      return;
    }
    if (Notification.permission !== "granted") {
      toast.error("Push not enabled. Click 'Enable push notifications' first.");
      return;
    }
    try {
      new Notification("RSI & MA Tracker — Test", {
        body: "This is a test push notification.",
        tag: "test-push",
      });
      toast.success("Test push sent");
    } catch (e) {
      toast.error("Failed to display notification: " + e.message);
    }
  };

  const testEmail = async () => {
    try {
      await api.testNotification();
      toast.success("Test email sent");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to send test email");
    }
  };

  if (!settings) return null;

  return (
    <div className="fixed inset-0 z-50 flex" data-testid="settings-panel">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative ml-auto w-full max-w-md h-full bg-white border-l border-[var(--border)] shadow-lg overflow-y-auto scrollbar-thin">
        <div className="sticky top-0 bg-white border-b border-[var(--border)] px-5 py-4 flex justify-between items-center">
          <div>
            <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
              Global Configuration
            </div>
            <h2 className="text-lg font-medium text-[var(--text-primary)]">Settings</h2>
          </div>
          <button
            data-testid="close-settings-btn"
            onClick={onClose}
            className="p-1.5 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-gray-50 rounded-sm transition-colors"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>

        <div className="px-5 py-6 space-y-8">
          {/* RSI */}
          <section>
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3 border-b border-[var(--border)] pb-2">
              RSI
            </h3>
            <div className="grid grid-cols-3 gap-3">
              <Field label="Period">
                <NumInput testid="rsi-period-input" value={settings.rsi_period} onChange={(v) => handleChange("rsi_period", v)} min={2} max={100} />
              </Field>
              <Field label="Lower">
                <NumInput testid="rsi-lower-input" value={settings.rsi_lower} onChange={(v) => handleChange("rsi_lower", v)} step={0.5} min={0} max={100} />
              </Field>
              <Field label="Upper">
                <NumInput testid="rsi-upper-input" value={settings.rsi_upper} onChange={(v) => handleChange("rsi_upper", v)} step={0.5} min={0} max={100} />
              </Field>
            </div>
          </section>

          {/* MA */}
          <section>
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3 border-b border-[var(--border)] pb-2">
              Moving Averages
            </h3>
            <Field label="Type">
              <div className="inline-flex border border-[var(--border)] rounded-sm overflow-hidden" data-testid="ma-type-toggle">
                {[
                  { v: "sma", label: "SMA" },
                  { v: "ema", label: "EMA" },
                ].map((o) => (
                  <button
                    key={o.v}
                    type="button"
                    onClick={() => handleChange("ma_type", o.v)}
                    className={`px-3 py-1.5 text-xs uppercase tracking-wider font-mono ${
                      settings.ma_type === o.v
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
              <Field label="Short Period">
                <NumInput testid="ma-short-input" value={settings.ma_short} onChange={(v) => handleChange("ma_short", v)} min={2} max={500} />
              </Field>
              <Field label="Long Period">
                <NumInput testid="ma-long-input" value={settings.ma_long} onChange={(v) => handleChange("ma_long", v)} min={2} max={500} />
              </Field>
            </div>
          </section>

          {/* Alerts */}
          <section>
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-1 border-b border-[var(--border)] pb-2">
              Alert Conditions
            </h3>
            <ToggleRow testid="toggle-rsi-low" label="RSI Low (oversold)" checked={settings.alert_rsi_low} onChange={(v) => handleChange("alert_rsi_low", v)} />
            <ToggleRow testid="toggle-rsi-high" label="RSI High (overbought)" checked={settings.alert_rsi_high} onChange={(v) => handleChange("alert_rsi_high", v)} />
            <ToggleRow testid="toggle-golden-cross" label="Golden Cross" checked={settings.alert_golden_cross} onChange={(v) => handleChange("alert_golden_cross", v)} />
            <ToggleRow testid="toggle-death-cross" label="Death Cross" checked={settings.alert_death_cross} onChange={(v) => handleChange("alert_death_cross", v)} />
            <ToggleRow testid="toggle-combo" label="⚡ Combo (RSI + Cross)" checked={settings.alert_combo} onChange={(v) => handleChange("alert_combo", v)} />
          </section>

          {/* Notifications */}
          <section>
            <h3 className="text-sm font-medium text-[var(--text-primary)] mb-3 border-b border-[var(--border)] pb-2">
              Notifications
            </h3>
            <Field label="Notification Email">
              <input
                data-testid="notification-email-input"
                type="email"
                value={settings.notification_email}
                onChange={(e) => handleChange("notification_email", e.target.value)}
                placeholder="you@example.com"
                className="w-full border border-[var(--border)] bg-white rounded-sm px-3 py-2 text-sm font-mono text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)]"
              />
            </Field>
            <button
              data-testid="test-email-btn"
              onClick={testEmail}
              className="mt-2 inline-flex items-center gap-1.5 border border-[var(--border)] hover:bg-gray-50 text-[var(--text-primary)] px-3 py-1.5 rounded-sm text-xs transition-colors"
            >
              <Send size={12} strokeWidth={1.5} /> Send test email
            </button>

            <div className="mt-4">
              <Field label="Browser Push">
                <div className="flex gap-2 flex-wrap">
                  <button
                    data-testid="enable-push-btn"
                    onClick={enablePush}
                    className="inline-flex items-center gap-1.5 border border-[var(--border)] hover:bg-gray-50 text-[var(--text-primary)] px-3 py-1.5 rounded-sm text-xs transition-colors"
                  >
                    {pushEnabled ? <Bell size={12} strokeWidth={1.5} /> : <BellOff size={12} strokeWidth={1.5} />}
                    {pushEnabled ? "Push enabled" : "Enable push notifications"}
                  </button>
                  {pushEnabled && (
                    <button
                      data-testid="test-push-btn"
                      onClick={testPush}
                      className="inline-flex items-center gap-1.5 border border-[var(--border)] hover:bg-gray-50 text-[var(--text-primary)] px-3 py-1.5 rounded-sm text-xs transition-colors"
                    >
                      <Send size={12} strokeWidth={1.5} /> Test push
                    </button>
                  )}
                </div>
              </Field>
            </div>
          </section>
        </div>

        <div className="sticky bottom-0 bg-white border-t border-[var(--border)] px-5 py-3 flex justify-end gap-2">
          <button
            data-testid="cancel-settings-btn"
            onClick={onClose}
            className="border border-[var(--border)] hover:bg-gray-50 text-[var(--text-primary)] px-4 py-2 rounded-sm text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            data-testid="save-settings-btn"
            onClick={save}
            disabled={saving}
            className="bg-[var(--brand)] hover:bg-[var(--brand-hover)] text-white px-4 py-2 rounded-sm text-sm font-medium transition-colors disabled:opacity-60"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
