import React, { useCallback, useEffect, useState } from "react";
import { Settings as SettingsIcon, LineChart } from "lucide-react";
import { Toaster, toast } from "sonner";

import { api } from "./lib/api";
import { registerServiceWorker } from "./lib/push";
import StatusBar from "./components/StatusBar";
import TickerRow from "./components/TickerRow";
import AddTickerCard from "./components/AddTickerCard";
import AlertHistory from "./components/AlertHistory";
import SettingsPanel from "./components/SettingsPanel";
import TickerSettingsSheet from "./components/TickerSettingsSheet";
import "./App.css";

function _noop() {}

export default function App() {
  const [tickers, setTickers] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [status, setStatus] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [configTicker, setConfigTicker] = useState(null);
  const [addError, setAddError] = useState(null);

  const loadAll = useCallback(async () => {
    try {
      const [t, a, st, s] = await Promise.all([
        api.listTickers(),
        api.listAlerts(),
        api.scanStatus(),
        api.getSettings(),
      ]);
      setTickers(t);
      setAlerts(a);
      setStatus(st);
      setSettings(s);
    } catch (e) {
      toast.error("Failed to load data");
    }
  }, []);

  useEffect(() => {
    (async () => {
      setLoading(true);
      registerServiceWorker();
      await loadAll();
      setLoading(false);
    })();
  }, [loadAll]);

  const handleAdd = async (symbol) => {
    setAddError(null);
    try {
      await api.addTicker(symbol);
      toast.success(`${symbol} added`);
      await loadAll();
    } catch (e) {
      const msg = e.response?.data?.detail || "Failed to add ticker";
      setAddError(msg);
      toast.error(msg);
    }
  };

  const handleDelete = async (symbol) => {
    try {
      await api.deleteTicker(symbol);
      toast.success(`${symbol} removed`);
      await loadAll();
    } catch (e) {
      toast.error(e.response?.data?.detail || `Failed to remove ${symbol}`);
    }
  };

  const handleRunScan = async () => {
    setRunning(true);
    const before = alerts.length;
    try {
      await api.runScan();
      const [a, st] = await Promise.all([api.listAlerts(), api.scanStatus()]);
      setAlerts(a);
      setStatus(st);
      await loadAll();
      const newCount = a.length - before;
      if (newCount > 0) toast.success(`Scan complete — ${newCount} new alert(s)`);
      else toast.success("Scan complete — no new alerts");
    } catch (e) {
      toast.error("Scan failed");
    } finally {
      setRunning(false);
    }
  };

  const handleClearAlerts = async () => {
    if (!window.confirm("Clear all alert history?")) return;
    try {
      await api.clearAlerts();
      setAlerts([]);
      toast.success("History cleared");
    } catch {
      toast.error("Failed to clear");
    }
  };

  return (
    <div className="App">
      <Toaster position="top-right" richColors />

      {/* Header */}
      <header className="border-b border-[var(--border)] bg-white sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[var(--brand)] rounded-sm flex items-center justify-center">
              <LineChart size={16} strokeWidth={1.5} className="text-white" />
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold">
                Daily Scan Engine
              </div>
              <h1 className="text-base font-medium text-[var(--text-primary)] -mt-0.5">StochRSI-Bollinger Scaner</h1>
            </div>
          </div>
          <button
            data-testid="open-settings-btn"
            onClick={() => setSettingsOpen(true)}
            className="inline-flex items-center gap-2 border border-[var(--border)] hover:bg-gray-50 text-[var(--text-primary)] px-3 py-1.5 rounded-sm text-sm font-medium transition-colors"
          >
            <SettingsIcon size={14} strokeWidth={1.5} />
            Settings
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 md:px-8 py-6 md:py-8 space-y-4">
        <StatusBar status={status} onRun={handleRunScan} running={running} />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-8 space-y-3" data-testid="ticker-list">
            <AddTickerCard onAdd={handleAdd} error={addError} />
            {loading ? (
              <div className="border border-[var(--border)] bg-white rounded-sm p-6 text-center text-xs font-mono text-[var(--text-tertiary)]">
                Loading...
              </div>
            ) : tickers.length === 0 ? (
              <div className="border border-[var(--border)] bg-white rounded-sm p-6 text-center text-xs font-mono text-[var(--text-tertiary)]">
                No assets tracked. Add one above.
              </div>
            ) : (
              tickers.map((t) => (
                <TickerRow
                  key={t.id || t.symbol}
                  ticker={t}
                  onDelete={handleDelete}
                  onConfigure={setConfigTicker}
                />
              ))
            )}
          </div>

          <div className="lg:col-span-4">
            <AlertHistory alerts={alerts} onClear={handleClearAlerts} />
          </div>
        </div>

        <footer className="pt-6 text-center text-[10px] font-mono uppercase tracking-[0.15em] text-[var(--text-tertiary)]">
          Data via Yahoo Finance · Scan once daily at {String(status?.scan_hour_utc ?? 20).padStart(2, "0")}:00 UTC
        </footer>
      </main>

      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={loadAll}
      />
      <TickerSettingsSheet
        key={configTicker?.symbol || "none"}
        ticker={configTicker}
        onClose={() => setConfigTicker(null)}
        onSaved={loadAll}
        globalSettings={settings}
      />
    </div>
  );
}
