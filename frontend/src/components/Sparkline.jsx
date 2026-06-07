import React from "react";

// Minimalist sparkline (SVG only, no axes/grid)
export default function Sparkline({ data = [], width = 120, height = 32, color }) {
  if (!data || data.length < 2) {
    return (
      <div style={{ width, height }} className="text-[10px] text-gray-400 font-mono flex items-center">—</div>
    );
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stepX = width / (data.length - 1);
  const points = data
    .map((v, i) => `${(i * stepX).toFixed(2)},${(height - ((v - min) / range) * height).toFixed(2)}`)
    .join(" ");
  const isUp = data[data.length - 1] >= data[0];
  const stroke = color || (isUp ? "#059669" : "#DC2626");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true">
      <polyline className="sparkline-line" points={points} stroke={stroke} />
    </svg>
  );
}
