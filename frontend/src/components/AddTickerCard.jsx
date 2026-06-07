import React, { useState } from "react";
import { Plus } from "lucide-react";

export default function AddTickerCard({ onAdd, error }) {
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!value.trim()) return;
    setSubmitting(true);
    try {
      await onAdd(value.trim().toUpperCase());
      setValue("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="border border-[var(--border)] bg-white rounded-sm p-4">
      <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-tertiary)] font-semibold mb-2">
        Add Asset
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          data-testid="add-ticker-input"
          type="text"
          placeholder="e.g. AAPL, MSFT, VT, SPY"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={submitting}
          className="flex-1 border border-[var(--border)] bg-white rounded-sm px-3 py-2 text-sm font-mono uppercase placeholder:normal-case placeholder:text-[var(--text-tertiary)] focus:outline-none focus:ring-1 focus:ring-[var(--brand)] focus:border-[var(--brand)]"
        />
        <button
          data-testid="add-ticker-btn"
          type="submit"
          disabled={submitting || !value.trim()}
          className="inline-flex items-center gap-1.5 bg-[var(--brand)] hover:bg-[var(--brand-hover)] text-white px-3 py-2 rounded-sm text-sm font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <Plus size={14} strokeWidth={1.5} />
          {submitting ? "Adding..." : "Add"}
        </button>
      </form>
      {error && (
        <div data-testid="add-ticker-error" className="mt-2 text-xs font-mono text-[var(--signal-sell)]">
          {error}
        </div>
      )}
    </div>
  );
}
